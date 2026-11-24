"""
Auto-Learning Dictionary Engine for Gemini Flow (Wispr Flow Parity).
Passively monitors a 5-second window immediately following a text injection.
If the user backspaces or types a manual correction over a pasted word,
identifies the substitution and automatically registers the phonetic/spelling
pair into the custom dictionary without stealing keyboard focus.
"""
import time
import logging
import threading
from typing import Callable, Optional, Dict, List, Set, Any, Tuple
from pynput import keyboard

logger = logging.getLogger("GeminiFlow.AutoLearner")


class AutoLearner:
    _active_monitor_thread: Optional[threading.Thread] = None
    _stop_monitor_event = threading.Event()
    _last_learned_pair: Optional[Tuple[str, str]] = None

    @classmethod
    def evaluate_correction(
        cls,
        words_in_paste: List[str],
        backspace_count: int,
        typed_chars: List[str]
    ) -> Optional[Tuple[str, str]]:
        """
        Pure evaluation logic for detecting manual word corrections:
        Enforces backspace threshold (>= 2), word length constraint (>= 3),
        and fuzzy prefix/length match against previous paste words.
        Returns (target_word, new_word) or None.
        """
        if backspace_count < 2 or not typed_chars:
            return None

        new_word = "".join(typed_chars).strip()
        if len(new_word) < 3 or any(ch in new_word for ch in " \t\n.,;"):
            return None

        for w in reversed(words_in_paste):
            if w.lower() != new_word.lower() and (
                w.lower().startswith(new_word[:2].lower()) or
                len(w) == len(new_word) or
                abs(len(w) - len(new_word)) <= 2
            ):
                return (w, new_word)
        return None

    @classmethod
    def start_post_paste_monitor(
        cls,
        pasted_text: str,
        config_manager: Any,
        on_learned_callback: Optional[Callable[[str, str], None]] = None,
        timeout_seconds: float = 5.0
    ):
        """
        Starts a 5-second lightweight listener watching for immediate manual word corrections.
        """
        if not pasted_text or len(pasted_text.strip()) < 2:
            return

        cls._stop_monitor_event.set()
        cls._stop_monitor_event = threading.Event()

        def _monitor_worker():
            stop_evt = cls._stop_monitor_event
            start_ts = time.time()
            words_in_paste = [w.strip(".,;:?!'\"()[]{}") for w in pasted_text.split() if len(w) >= 3]
            if not words_in_paste:
                return

            backspace_count = 0
            typed_chars: List[str] = []

            def _on_press(key):
                nonlocal backspace_count
                try:
                    if key == keyboard.Key.backspace:
                        if typed_chars:
                            typed_chars.pop()
                        else:
                            backspace_count += 1
                    elif hasattr(key, "char") and key.char:
                        typed_chars.append(key.char)
                except Exception:
                    pass

            listener = keyboard.Listener(on_press=_on_press)
            listener.start()

            try:
                while (time.time() - start_ts) < timeout_seconds and not stop_evt.is_set():
                    time.sleep(0.1)

                listener.stop()

                pair = cls.evaluate_correction(words_in_paste, backspace_count, typed_chars)
                if pair:
                    target_word, new_word = pair
                    logger.info(f"[AUTO-LEARNER] Detected manual correction: '{target_word}' -> '{new_word}'")
                    cls._last_learned_pair = (target_word, new_word)

                    # Persist to custom dictionary
                    try:
                        if config_manager and hasattr(config_manager, "add_dictionary_pair"):
                            config_manager.add_dictionary_pair(target_word, new_word)
                        elif config_manager and hasattr(config_manager, "set_dictionary"):
                            curr_dict = list(config_manager.get_dictionary() or [])
                            curr_dict.append({"spoken": target_word, "replacement": new_word})
                            config_manager.set_dictionary(curr_dict)
                        elif config_manager and hasattr(config_manager, "get_dictionary"):
                            curr_dict = list(config_manager.get_dictionary() or [])
                            curr_dict.append({"spoken": target_word, "replacement": new_word})
                            if hasattr(config_manager, "set"):
                                config_manager.set("dictionary", curr_dict)
                            if hasattr(config_manager, "save_config"):
                                config_manager.save_config()

                        from app.vocabulary.vocab_engine import VocabEngine
                        VocabEngine.get_instance().add_pair(target_word, new_word)
                    except Exception as ex:
                        logger.debug(f"Auto-learn persistence error: {ex}")

                    if on_learned_callback:
                        try:
                            on_learned_callback(target_word, new_word)
                        except Exception:
                            pass
            except Exception as e:
                logger.debug(f"AutoLearner error: {e}")
            finally:
                try:
                    listener.stop()
                except Exception:
                    pass

        cls._active_monitor_thread = threading.Thread(
            target=_monitor_worker, daemon=True, name="AutoLearnerMonitor"
        )
        cls._active_monitor_thread.start()

    @classmethod
    def undo_last_learned(cls, config_manager: Any) -> bool:
        """Reverts the last auto-learned dictionary entry if user clicks Undo."""
        if not cls._last_learned_pair:
            return False
        target_word, new_word = cls._last_learned_pair
        try:
            if config_manager and hasattr(config_manager, "remove_dictionary_pair"):
                config_manager.remove_dictionary_pair(target_word, new_word)
            elif config_manager and hasattr(config_manager, "set_dictionary"):
                curr = list(config_manager.get_dictionary() or [])
                filtered = [d for d in curr if not (d.get("spoken") == target_word and d.get("replacement") == new_word)]
                config_manager.set_dictionary(filtered)
            elif config_manager and hasattr(config_manager, "get_dictionary"):
                curr = list(config_manager.get_dictionary() or [])
                filtered = [d for d in curr if not (d.get("spoken") == target_word and d.get("replacement") == new_word)]
                if hasattr(config_manager, "set"):
                    config_manager.set("dictionary", filtered)
                if hasattr(config_manager, "save_config"):
                    config_manager.save_config()

            # Revert from in-memory and on-disk VocabEngine
            try:
                from app.vocabulary.vocab_engine import VocabEngine
                ve = VocabEngine.get_instance()
                if hasattr(ve, "remove_pair"):
                    ve.remove_pair(target_word, new_word)
                else:
                    ve.delete_entry(new_word)
            except Exception as ve_err:
                logger.debug(f"AutoLearner VocabEngine undo note: {ve_err}")

            logger.info(f"[AUTO-LEARNER] Reverted learned pair: '{target_word}' -> '{new_word}'")
            cls._last_learned_pair = None
            return True
        except Exception as e:
            logger.debug(f"Error reverting auto-learned pair: {e}")
            return False
