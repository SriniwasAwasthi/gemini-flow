import os
import io
import wave
import time
import tempfile
import logging
from typing import Tuple, Optional

logger = logging.getLogger('GeminiFlow.OfflineSpeech')

class OfflineSpeechEngine:
    @classmethod
    def transcribe_wav(cls, wav_bytes: bytes) -> Tuple[bool, str]:
        if not wav_bytes or len(wav_bytes) < 800:
            return False, 'Audio is too short or empty.'

        try:
            success, text = cls._transcribe_with_sapi(wav_bytes)
            if success and text.strip():
                logger.info(f'Offline SAPI recognition succeeded: {text[:60]}...')
                return True, text.strip()
        except Exception as e:
            logger.debug(f'SAPI offline transcription exception: {e}')

        try:
            success, text = cls._transcribe_with_sr(wav_bytes)
            if success and text.strip():
                logger.info(f'Offline speech_recognition succeeded: {text[:60]}...')
                return True, text.strip()
        except Exception as e:
            logger.debug(f'speech_recognition offline fallback note: {e}')

        return False, 'Local offline speech recognition could not decode audio. Please check microphone.'

    @classmethod
    def _transcribe_with_sapi(cls, wav_bytes: bytes) -> Tuple[bool, str]:
        tmp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        tmp_path = tmp_file.name
        try:
            tmp_file.write(wav_bytes)
            tmp_file.flush()
            tmp_file.close()

            import pythoncom
            import win32com.client

            pythoncom.CoInitialize()
            try:
                recognized_phrases = []

                class RecoEvents:
                    def OnRecognition(self, StreamNumber, StreamPosition, RecognitionType, Result):
                        try:
                            t = Result.PhraseInfo.GetText()
                            if t:
                                recognized_phrases.append(t)
                        except Exception as ex:
                            logger.debug(f'RecoEvents OnRecognition extract error: {ex}')

                    def OnFalseRecognition(self, StreamNumber, StreamPosition, Result):
                        pass

                recognizer = win32com.client.Dispatch('SAPI.SpInprocRecognizer')
                context = recognizer.CreateRecoContext()
                handler = win32com.client.WithEvents(context, RecoEvents)
                grammar = context.CreateGrammar()
                grammar.DictationSetState(1)

                stream = win32com.client.Dispatch('SAPI.SpFileStream')
                stream.Open(tmp_path, 3)
                recognizer.AudioInputStream = stream

                start_t = time.time()
                dur = max(0.5, len(wav_bytes) / 32000.0)
                timeout_limit = min(10.0, dur * 1.5 + 1.0)

                while time.time() - start_t < timeout_limit:
                    pythoncom.PumpWaitingMessages()
                    time.sleep(0.04)

                try:
                    stream.Close()
                except Exception:
                    pass

                final_text = ' '.join(recognized_phrases).strip()
                if final_text:
                    return True, final_text
                return False, 'No speech detected by offline SAPI engine.'
            finally:
                pythoncom.CoUninitialize()
        finally:
            try:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            except Exception:
                pass

    @classmethod
    def _transcribe_with_sr(cls, wav_bytes: bytes) -> Tuple[bool, str]:
        try:
            import speech_recognition as sr
            r = sr.Recognizer()
            with sr.AudioFile(io.BytesIO(wav_bytes)) as source:
                audio_data = r.record(source)
            if hasattr(r, 'recognize_sphinx'):
                try:
                    text = r.recognize_sphinx(audio_data)
                    if text:
                        return True, text
                except Exception:
                    pass
            return False, 'Offline SR engine not available.'
        except Exception as e:
            return False, str(e)
