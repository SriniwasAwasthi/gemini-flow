"""
Languages Catalog & Multilingual Intelligence for Gemini Flow.
Provides 210+ comprehensive world languages across Indian & South Asian, European,
East & Southeast Asian, Middle Eastern & Central Asian, African, and Americas/Indigenous regions.
Supports live search, region filtering, and strict target language AI prompt conditioning.
"""
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Any, Tuple
import difflib


@dataclass
class LanguageItem:
    code: str           # ISO 639-1 / 639-3 code (e.g., 'mr', 'hi', 'en', 'es')
    name: str           # English name (e.g., 'Marathi', 'Spanish')
    native_name: str    # Native script name (e.g., 'मराठी', 'Español')
    region: str         # Region category
    flag: str           # Flag emoji or regional symbol
    script: str         # Writing script (e.g., 'Devanagari', 'Latin')
    sample_hints: str = "" # Acoustic/grammatical cue words for LLM priming

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LanguageItem":
        return cls(**data)


# Region categories for quick filtering
REGION_ALL = "All"
REGION_INDIAN = "Indian & South Asian"
REGION_EUROPEAN = "Major European"
REGION_ASIAN = "East & Southeast Asian"
REGION_MIDDLE_EAST = "Middle Eastern & Central Asian"
REGION_AFRICAN = "African"
REGION_AMERICAS = "Americas & Indigenous"

REGIONS = [
    REGION_ALL,
    REGION_INDIAN,
    REGION_EUROPEAN,
    REGION_ASIAN,
    REGION_MIDDLE_EAST,
    REGION_AFRICAN,
    REGION_AMERICAS
]


LANGUAGES_DB: List[LanguageItem] = [
    # =========================================================================
    # 1. INDIAN & SOUTH ASIAN LANGUAGES (35 Languages)
    # =========================================================================
    LanguageItem("mr", "Marathi", "मराठी", REGION_INDIAN, "🇮🇳", "Devanagari", "आहे, नाही, करतो, बोलतो, नमस्कार, कसे आहात, छान, आज"),
    LanguageItem("hi", "Hindi", "हिन्दी", REGION_INDIAN, "🇮🇳", "Devanagari", "है, नहीं, करता, बोलता, नमस्ते, कैसे हैं, अच्छा, आज"),
    LanguageItem("sa", "Sanskrit", "संस्कृतम्", REGION_INDIAN, "🇮🇳", "Devanagari", "अस्ति, नास्ति, करोति, वदति, नमस्ते, कथम् अस्ति"),
    LanguageItem("ta", "Tamil", "தமிழ்", REGION_INDIAN, "🇮🇳", "Tamil", "வணக்கம், எப்படி இருக்கிறீர்கள், ஆம், இல்லை, நன்றி"),
    LanguageItem("te", "Telugu", "తెలుగు", REGION_INDIAN, "🇮🇳", "Telugu", "నమస్కారం, ఎలా ఉన్నారు, అవును, కాదు, ధన్యవాదాలు"),
    LanguageItem("kn", "Kannada", "ಕನ್ನಡ", REGION_INDIAN, "🇮🇳", "Kannada", "ನಮಸ್ಕಾರ, ಹೇಗಿದ್ದೀರಾ, ಹೌದು, ಇಲ್ಲ, ಧನ್ಯವಾದಗಳು"),
    LanguageItem("ml", "Malayalam", "മലയാളം", REGION_INDIAN, "🇮🇳", "Malayalam", "നമസ്കാരം, എങ്ങനെയുണ്ട്, അതെ, അല്ല, നന്ദി"),
    LanguageItem("bn", "Bengali", "বাংলা", REGION_INDIAN, "🇮🇳", "Bengali", "নমস্কার, কেমন আছেন, হ্যাঁ, না, ধন্যবাদ"),
    LanguageItem("gu", "Gujarati", "ગુજરાતી", REGION_INDIAN, "🇮🇳", "Gujarati", "નમસ્તે, કેમ છો, હા, ના, આભાર"),
    LanguageItem("pa", "Punjabi", "ਪੰਜਾਬੀ", REGION_INDIAN, "🇮🇳", "Gurmukhi", "ਸਤਿ ਸ੍ਰੀ ਅਕਾਲ, ਕਿਵੇਂ ਹੋ, ਹਾਂ, ਨਹੀਂ, ਧੰਨਵਾਦ"),
    LanguageItem("or", "Odia", "ଓଡ଼ିଆ", REGION_INDIAN, "🇮🇳", "Odia", "ନମସ୍କାର, କେମିତି ଅଛନ୍ତି, ହଁ, ନାହିଁ, ଧନ୍ୟବାଦ"),
    LanguageItem("as", "Assamese", "অসমীয়া", REGION_INDIAN, "🇮🇳", "Bengali", "নমস্কাৰ, কেনে আছে, হয়, নহয়, ধন্যবাদ"),
    LanguageItem("ur", "Urdu", "اردو", REGION_INDIAN, "🇵🇰", "Arabic", "السلام علیکم, آپ کیسے ہیں, جی ہاں, نہیں, شکریہ"),
    LanguageItem("ne", "Nepali", "नेपाली", REGION_INDIAN, "🇳🇵", "Devanagari", "नमस्ते, तपाईँलाई कस्तो छ, हो, होइन, धन्यवाद"),
    LanguageItem("kok", "Konkani", "कोंकणी", REGION_INDIAN, "🇮🇳", "Devanagari", "नमस्कार, कशे आसात, हय, ना, देव बरे करूं"),
    LanguageItem("sd", "Sindhi", "سنڌي / सिन्धी", REGION_INDIAN, "🇮🇳", "Arabic / Devanagari", "سلام, توهان ڪيئن آهيو, ها, نه, مهرباني"),
    LanguageItem("mai", "Maithili", "मैथिली", REGION_INDIAN, "🇮🇳", "Devanagari", "प्रणाम, अपने केहन छी, हँ, नहि, धन्यवाद"),
    LanguageItem("doi", "Dogri", "डोगरी", REGION_INDIAN, "🇮🇳", "Devanagari", "नमस्ते, तुंदा केह् हाल ऐ, हाँ, नेईं, धन्यवाद"),
    LanguageItem("ks", "Kashmiri", "कॉशुर / كٲشُر", REGION_INDIAN, "🇮🇳", "Arabic / Devanagari", "سلام, توہِ چھِوا ٹھیک, آ, نہ, شکریہ"),
    LanguageItem("sat", "Santali", "ᱥᱟᱱᱛᱟᱲᱤ", REGION_INDIAN, "🇮🇳", "Ol Chiki", "ᱡᱚᱦᱟᱨ, ᱪᱮᱫ ᱞᱮᱠᱟ ᱢᱮᱱᱟᱜ ᱵᱤᱱᱟ, ᱦᱮᱸ, ᱵᱟᱝ"),
    LanguageItem("brx", "Bodo", "बड़ो", REGION_INDIAN, "🇮🇳", "Devanagari", "खुलुमबाय, नोंथाङा माबोरै दं, ओ, नङा, साबायखर"),
    LanguageItem("mni", "Manipuri (Meitei)", "মৈতৈলোন্", REGION_INDIAN, "🇮🇳", "Meetei Mayek / Bengali", "খুরুমজরি, কমদৌরিগে, য়ারে, নত্তে, থাগৎচরি"),
    LanguageItem("si", "Sinhala", "සිංහල", REGION_INDIAN, "🇱🇰", "Sinhala", "ආයුබෝවන්, කොහොමද, ඔව්, නැහැ, ස්තූතියි"),
    LanguageItem("bho", "Bhojpuri", "भोजपुरी", REGION_INDIAN, "🇮🇳", "Devanagari", "प्रणाम, का हाल बा, हाँ, ना, धन्यबाद"),
    LanguageItem("mwr", "Marwari", "मारवाड़ी", REGION_INDIAN, "🇮🇳", "Devanagari", "खम्मा घणी, कई हाल चाल है, हाँ, कोनी, धन्यवाद"),
    LanguageItem("hne", "Chhattisgarhi", "छत्तीसगढ़ी", REGION_INDIAN, "🇮🇳", "Devanagari", "जय जोहार, कसन हवव, हव, नइ, धन्यवाद"),
    LanguageItem("bgc", "Haryanvi", "हरियाणवी", REGION_INDIAN, "🇮🇳", "Devanagari", "राम राम, के हाल चाल सै, हाँ, ना, धन्यवाद"),
    LanguageItem("mag", "Magahi", "मगही", REGION_INDIAN, "🇮🇳", "Devanagari", "प्रणाम, केहन हई, हाँ, नइखे, धन्यवाद"),
    LanguageItem("tcy", "Tulu", "ತುಳು", REGION_INDIAN, "🇮🇳", "Kannada", "ನಮಸ್ಕಾರ, ಎಂಚ ಉಲ್ಲರ್, ಅಂದ್, ಅತ್ತ್, ಸೊಲ್ಮೆಲು"),
    LanguageItem("bo", "Tibetan", "བོད་སྐད་", REGION_INDIAN, "🇮🇳", "Tibetan", "བཀྲ་ཤིས་བདེ་ལེགས, ཁྱེད་རང་སྐུ་གཟུགས་བདེ་པོ་ཡིན་པས"),
    LanguageItem("raj", "Rajasthani", "राजस्थानी", REGION_INDIAN, "🇮🇳", "Devanagari", "राम राम सा, कांई हाल चाल है, हाँ, नहीं"),
    LanguageItem("awa", "Awadhi", "अवधी", REGION_INDIAN, "🇮🇳", "Devanagari", "प्रनाम, का हाल अहई, हाँ, नाहीं"),
    LanguageItem("gbm", "Garhwali", "गढ़वाली", REGION_INDIAN, "🇮🇳", "Devanagari", "नमस्कार, क्या हाल छन, हाँ, नी"),
    LanguageItem("kfy", "Kumaoni", "कुमाऊँनी", REGION_INDIAN, "🇮🇳", "Devanagari", "पैलाग, कस हाल चाल छ, हाँ, न"),

    # =========================================================================
    # 2. MAJOR EUROPEAN LANGUAGES (60 Languages)
    # =========================================================================
    LanguageItem("en", "English", "English", REGION_EUROPEAN, "🌐", "Latin", "hello, how are you, yes, no, thank you"),
    LanguageItem("es", "Spanish", "Español", REGION_EUROPEAN, "🇪🇸", "Latin", "hola, cómo estás, sí, no, gracias, por favor"),
    LanguageItem("fr", "French", "Français", REGION_EUROPEAN, "🇫🇷", "Latin", "bonjour, comment allez-vous, oui, non, merci"),
    LanguageItem("de", "German", "Deutsch", REGION_EUROPEAN, "🇩🇪", "Latin", "guten Tag, wie geht es dir, ja, nein, danke"),
    LanguageItem("it", "Italian", "Italiano", REGION_EUROPEAN, "🇮🇹", "Latin", "ciao, come stai, sì, no, grazie, per favore"),
    LanguageItem("pt", "Portuguese", "Português", REGION_EUROPEAN, "🇵🇹", "Latin", "olá, como vai você, sim, não, obrigado"),
    LanguageItem("ru", "Russian", "Русский", REGION_EUROPEAN, "🇷🇺", "Cyrillic", "здравствуйте, как дела, да, нет, спасибо"),
    LanguageItem("nl", "Dutch", "Nederlands", REGION_EUROPEAN, "🇳🇱", "Latin", "hallo, hoe gaat het, ja, nee, dank je"),
    LanguageItem("pl", "Polish", "Polski", REGION_EUROPEAN, "🇵🇱", "Latin", "cześć, jak się masz, tak, nie, dziękuję"),
    LanguageItem("sv", "Swedish", "Svenska", REGION_EUROPEAN, "🇸🇪", "Latin", "hej, hur mår du, ja, nej, tack"),
    LanguageItem("uk", "Ukrainian", "Українська", REGION_EUROPEAN, "🇺🇦", "Cyrillic", "привіт, як справи, так, ні, дякую"),
    LanguageItem("el", "Greek", "Ελληνικά", REGION_EUROPEAN, "🇬🇷", "Greek", "γεια σας, πώς είστε, ναι, όχι, ευχαριστώ"),
    LanguageItem("cs", "Czech", "Čeština", REGION_EUROPEAN, "🇨🇿", "Latin", "ahoj, jak se máš, ano, ne, děkuji"),
    LanguageItem("ro", "Romanian", "Română", REGION_EUROPEAN, "🇷🇴", "Latin", "salut, ce mai faci, da, nu, mulțumesc"),
    LanguageItem("hu", "Hungarian", "Magyar", REGION_EUROPEAN, "🇭🇺", "Latin", "szia, hogy vagy, igen, nem, köszönöm"),
    LanguageItem("da", "Danish", "Dansk", REGION_EUROPEAN, "🇩🇰", "Latin", "hej, hvordan har du det, ja, nej, tak"),
    LanguageItem("fi", "Finnish", "Suomi", REGION_EUROPEAN, "🇫🇮", "Latin", "hei, mitä kuuluu, kyllä, ei, kiitos"),
    LanguageItem("no", "Norwegian", "Norsk", REGION_EUROPEAN, "🇳🇴", "Latin", "hei, hvordan har du det, ja, nei, takk"),
    LanguageItem("sk", "Slovak", "Slovenčina", REGION_EUROPEAN, "🇸🇰", "Latin", "ahoj, ako sa máš, áno, nie, ďakujem"),
    LanguageItem("hr", "Croatian", "Hrvatski", REGION_EUROPEAN, "🇭🇷", "Latin", "bok, kako si, da, ne, hvala"),
    LanguageItem("bg", "Bulgarian", "Български", REGION_EUROPEAN, "🇧🇬", "Cyrillic", "здравейте, как сте, да, не, благодаря"),
    LanguageItem("sr", "Serbian", "Српски", REGION_EUROPEAN, "🇷🇸", "Cyrillic / Latin", "здраво, како си, да, не, хвала"),
    LanguageItem("ca", "Catalan", "Català", REGION_EUROPEAN, "🇪🇸", "Latin", "hola, com estàs, sí, no, gràcies"),
    LanguageItem("eu", "Basque", "Euskara", REGION_EUROPEAN, "🇪🇸", "Latin", "kaixo, nola zaude, bai, ez, eskerrik asko"),
    LanguageItem("gl", "Galician", "Galego", REGION_EUROPEAN, "🇪🇸", "Latin", "ola, como estás, si, non, grazas"),
    LanguageItem("ga", "Irish", "Gaeilge", REGION_EUROPEAN, "🇮🇪", "Latin", "dia dhuit, conas atá tú, tá, níl, go raibh maith agat"),
    LanguageItem("cy", "Welsh", "Cymraeg", REGION_EUROPEAN, "🇬🇧", "Latin", "helo, sut wyt ti, ie, na, diolch"),
    LanguageItem("gd", "Scottish Gaelic", "Gàidhlig", REGION_EUROPEAN, "🇬🇧", "Latin", "halò, ciamar a tha thu, tha, chan eil, tapadh leat"),
    LanguageItem("is", "Icelandic", "Íslenska", REGION_EUROPEAN, "🇮🇸", "Latin", "halló, hvernig hefurðu það, já, nei, takk"),
    LanguageItem("sq", "Albanian", "Shqip", REGION_EUROPEAN, "🇦🇱", "Latin", "përshëndetje, si jeni, po, jo, faleminderit"),
    LanguageItem("lt", "Lithuanian", "Lietuvių", REGION_EUROPEAN, "🇱🇹", "Latin", "labas, kaip sekasi, taip, ne, ačiū"),
    LanguageItem("lv", "Latvian", "Latviešu", REGION_EUROPEAN, "🇱🇻", "Latin", "sveiki, kā tev iet, jā, nē, paldies"),
    LanguageItem("et", "Estonian", "Eesti", REGION_EUROPEAN, "🇪🇪", "Latin", "tere, kuidas läheb, jah, ei, aitäh"),
    LanguageItem("sl", "Slovenian", "Slovenščina", REGION_EUROPEAN, "🇸🇮", "Latin", "živijo, kako si, da, ne, hvala"),
    LanguageItem("bs", "Bosnian", "Bosanski", REGION_EUROPEAN, "🇧🇦", "Latin", "zdravo, kako si, da, ne, hvala"),
    LanguageItem("mk", "Macedonian", "Македонски", REGION_EUROPEAN, "🇲🇰", "Cyrillic", "здраво, како си, да, не, благодарам"),
    LanguageItem("mt", "Maltese", "Malti", REGION_EUROPEAN, "🇲🇹", "Latin", "bonġu, kif int, iva, le, grazzi"),
    LanguageItem("lb", "Luxembourgish", "Lëtzebuergesch", REGION_EUROPEAN, "🇱🇺", "Latin", "moien, wéi geet et, jo, nee, merci"),
    LanguageItem("be", "Belarusian", "Беларуская", REGION_EUROPEAN, "🇧🇾", "Cyrillic", "прывітанне, як справы, так, не, дзякуй"),
    LanguageItem("fo", "Faroese", "Føroyskt", REGION_EUROPEAN, "🇫🇴", "Latin", "halló, hvussu gongur, ja, nei, takk"),
    LanguageItem("br", "Breton", "Brezhoneg", REGION_EUROPEAN, "🇫🇷", "Latin", "demat, penaos emañ kont, ya, nann, trugarez"),
    LanguageItem("co", "Corsican", "Corsu", REGION_EUROPEAN, "🇫🇷", "Latin", "bonghjornu, cumu va, iè, nò, grazie"),
    LanguageItem("oc", "Occitan", "Occitan", REGION_EUROPEAN, "🇫🇷", "Latin", "adieu, coma va, òc, non, mercé"),
    LanguageItem("rm", "Romansh", "Rumantsch", REGION_EUROPEAN, "🇨🇭", "Latin", "allegra, co va, gea, na, grazia"),
    LanguageItem("yi", "Yiddish", "ייִדיש", REGION_EUROPEAN, "🇮🇱", "Hebrew", "שלום־עליכם, װאָס מאַכסטו, יאָ, נײן, אַ דאַנק"),
    LanguageItem("la", "Latin", "Latina", REGION_EUROPEAN, "🏛️", "Latin", "salve, quomodo vales, ita, minime, gratias"),
    LanguageItem("eo", "Esperanto", "Esperanto", REGION_EUROPEAN, "🌐", "Latin", "saluton, kiel vi fartas, jes, ne, dankon"),
    LanguageItem("fy", "Frisian", "Frysk", REGION_EUROPEAN, "🇳🇱", "Latin", "hallo, hoe giet it, ja, nee, tank"),
    LanguageItem("wa", "Walloon", "Walon", REGION_EUROPEAN, "🇧🇪", "Latin", "bondjoû, comint va-t-i, oyi, neni, gråces"),
    LanguageItem("sc", "Sardinian", "Sardu", REGION_EUROPEAN, "🇮🇹", "Latin", "bonas tardas, comente istas, eja, no, gràtzias"),
    LanguageItem("scn", "Sicilian", "Sicilianu", REGION_EUROPEAN, "🇮🇹", "Latin", "ciao, comu stai, sì, no, grazzii"),
    LanguageItem("vec", "Venetian", "Vèneto", REGION_EUROPEAN, "🇮🇹", "Latin", "ciao, come steto, sì, no, grasie"),
    LanguageItem("an", "Aragonese", "Aragonés", REGION_EUROPEAN, "🇪🇸", "Latin", "hola, cómo yes, sí, no, gracias"),
    LanguageItem("ast", "Asturian", "Asturianu", REGION_EUROPEAN, "🇪🇸", "Latin", "hola, cómo tas, sí, non, gracies"),
    LanguageItem("gv", "Manx", "Gaelg", REGION_EUROPEAN, "🇮🇲", "Latin", "moghrey mie, kys t'ou, ta, cha nel, gura mie ayd"),
    LanguageItem("kw", "Cornish", "Kernewek", REGION_EUROPEAN, "🇬🇧", "Latin", "dydh da, fatla genes, ya, na, meur ras"),

    # =========================================================================
    # 3. EAST & SOUTHEAST ASIAN LANGUAGES (35 Languages)
    # =========================================================================
    LanguageItem("ja", "Japanese", "日本語", REGION_ASIAN, "🇯🇵", "Japanese", "こんにちは, どうですか, はい, いいえ, ありがとう, です, ます"),
    LanguageItem("zh-CN", "Chinese (Simplified)", "简体中文", REGION_ASIAN, "🇨🇳", "Simplified Han", "你好, 你好吗, 是的, 不是, 谢谢, 请"),
    LanguageItem("zh-TW", "Chinese (Traditional)", "繁體中文", REGION_ASIAN, "🇹🇼", "Traditional Han", "你好, 你好嗎, 是的, 不是, 謝謝, 請"),
    LanguageItem("yue", "Cantonese", "粵語 / 廣東話", REGION_ASIAN, "🇭🇰", "Traditional Han", "雷好, 點呀, 係, 唔係, 多謝, 唔該"),
    LanguageItem("ko", "Korean", "한국어", REGION_ASIAN, "🇰🇷", "Hangul", "안녕하세요, 어떻게 지내세요, 네, 아니요, 감사합니다"),
    LanguageItem("vi", "Vietnamese", "Tiếng Việt", REGION_ASIAN, "🇻🇳", "Latin", "xin chào, bạn khỏe không, có, không, cảm ơn"),
    LanguageItem("th", "Thai", "ไทย", REGION_ASIAN, "🇹🇭", "Thai", "สวัสดี, สบายดีไหม, ใช่, ไม่, ขอบคุณ, ครับ, ค่ะ"),
    LanguageItem("id", "Indonesian", "Bahasa Indonesia", REGION_ASIAN, "🇮🇩", "Latin", "halo, apa kabar, ya, tidak, terima kasih"),
    LanguageItem("ms", "Malay", "Bahasa Melayu", REGION_ASIAN, "🇲🇾", "Latin", "helo, apa khabar, ya, tidak, terima kasih"),
    LanguageItem("tl", "Tagalog / Filipino", "Wikang Filipino", REGION_ASIAN, "🇵🇭", "Latin", "kamusta, mabuti, oo, hindi, salamat"),
    LanguageItem("my", "Burmese", "မြန်မာဘာသာ", REGION_ASIAN, "🇲🇲", "Burmese", "မင်္ဂလာပါ, နေကောင်းလား, ဟုတ်တယ်, မဟုတ်ဘူး, ကျေးဇူးတင်ပါတယ်"),
    LanguageItem("km", "Khmer", "ភាសាខ្មែរ", REGION_ASIAN, "🇰🇭", "Khmer", "សួស្តី, តើអ្នកសុខសប្បាយទេ, បាទ, ទេ, អរគុណ"),
    LanguageItem("lo", "Lao", "ພາສາລາວ", REGION_ASIAN, "🇱🇦", "Lao", "ສະບາຍດີ, ສະບາຍດີບໍ, ແມ່ນ, ບໍ່, ຂອບໃຈ"),
    LanguageItem("mn", "Mongolian", "Монгол хэл", REGION_ASIAN, "🇲🇳", "Cyrillic", "сайн байна уу, ямар байна, тийм, үгүй, баярлалаа"),
    LanguageItem("jv", "Javanese", "Basa Jawa", REGION_ASIAN, "🇮🇩", "Latin", "sugeng rawuh, piye kabare, iya, ora, matur nuwun"),
    LanguageItem("su", "Sundanese", "Basa Sunda", REGION_ASIAN, "🇮🇩", "Latin", "wilujeng sumping, kumaha damang, muhun, henteu, hatur nuhun"),
    LanguageItem("ceb", "Cebuano", "Bisaya", REGION_ASIAN, "🇵🇭", "Latin", "kumusta, maayo, oo, dili, salamat"),
    LanguageItem("ilo", "Ilocano", "Ti Pagsasao nga Ilokano", REGION_ASIAN, "🇵🇭", "Latin", "kablaaw, kumustaka, wen, saan, agyamanak"),
    LanguageItem("hil", "Hiligaynon", "Ilonggo", REGION_ASIAN, "🇵🇭", "Latin", "kamusta, maayo, huo, indi, salamat"),
    LanguageItem("hmn", "Hmong", "Hmoob", REGION_ASIAN, "🌐", "Latin", "nyob zoo, koj nyob li cas, yog, tsis yog, ua tsaug"),
    LanguageItem("ug", "Uyghur", "ئۇيغۇرچە", REGION_ASIAN, "🇨🇳", "Arabic", "ياخشىمۇسىز, ئەھۋالىڭىز قانداق, ھەئە, ياق, رەھمەت"),
    LanguageItem("nan", "Min Nan / Hokkien", "閩南語", REGION_ASIAN, "🇹🇼", "Traditional Han", "汝好, 食飽未, 是, 毋是, 多謝"),
    LanguageItem("hak", "Hakka", "客家話", REGION_ASIAN, "🇨🇳", "Traditional Han", "汝好, 食飽吂, 係, 毋係, 恁仔細"),
    LanguageItem("wuu", "Wu / Shanghainese", "吴语", REGION_ASIAN, "🇨🇳", "Simplified Han", "侬好, 哪亨, 是个, 勿是, 谢谢侬"),
    LanguageItem("ban", "Balinese", "Basa Bali", REGION_ASIAN, "🇮🇩", "Latin", "om swastiastu, punapi gatra, inggih, nenten, suksma"),
    LanguageItem("mad", "Madurese", "Basa Madhura", REGION_ASIAN, "🇮🇩", "Latin", "salam, kemma kabarra, iya, enja', mator sakalangkong"),
    LanguageItem("min", "Minangkabau", "Baso Minang", REGION_ASIAN, "🇮🇩", "Latin", "halo, baa kaba, iyo, indak, tarimo kasih"),
    LanguageItem("bug", "Buginese", "Basa Ugi", REGION_ASIAN, "🇮🇩", "Latin", "salam, aga kareba, iye, de', kurru sumange"),
    LanguageItem("ace", "Acehnese", "Bahsa Acèh", REGION_ASIAN, "🇮🇩", "Latin", "salam, peue haba, nyoe, h'an, teurimong gaséh"),
    LanguageItem("tet", "Tetum", "Lia-Tetun", REGION_ASIAN, "🇹🇱", "Latin", "olá, di'ak ka lae, sin, lae, obrigadu"),
    LanguageItem("dz", "Dzongkha", "རྫོང་ཁ", REGION_ASIAN, "🇧🇹", "Tibetan", "कुज़ूज़ांग्पो ला, गदेबे य़ोए, इन, मेन, काद्रीनछे ला"),

    # =========================================================================
    # 4. MIDDLE EASTERN & CENTRAL ASIAN LANGUAGES (30 Languages)
    # =========================================================================
    LanguageItem("ar", "Arabic (Standard)", "العربية الفصحى", REGION_MIDDLE_EAST, "🇸🇦", "Arabic", "مرحبا, كيف حالك, نعم, لا, شكرا, السلام عليكم"),
    LanguageItem("arz", "Arabic (Egyptian)", "العربية المصرية", REGION_MIDDLE_EAST, "🇪🇬", "Arabic", "أهلا, ازيك, عامل ايه, ايوه, لا, شكرا"),
    LanguageItem("apc", "Arabic (Levantine)", "العربية الشامية", REGION_MIDDLE_EAST, "🇱🇧", "Arabic", "مرحبا, كيفك, شو أخبارك, اي, لاء, شكرا"),
    LanguageItem("afb", "Arabic (Gulf)", "اللهجة الخليجية", REGION_MIDDLE_EAST, "🇦🇪", "Arabic", "هلا, شلونك, شخبارك, إي, لا, مشكور"),
    LanguageItem("ary", "Arabic (Maghrebi / Darija)", "الدارجة المغربية", REGION_MIDDLE_EAST, "🇲🇦", "Arabic", "السلام, كيدير, لاباس, اه, لا, شكرا بزاف"),
    LanguageItem("fa", "Persian / Farsi", "فارسی", REGION_MIDDLE_EAST, "🇮🇷", "Arabic", "سلام, حال شما چطوره, بله, خیر, خیلی ممنون"),
    LanguageItem("prs", "Dari", "دری", REGION_MIDDLE_EAST, "🇦🇫", "Arabic", "سلام, چطور هستید, بله, نی, تشکر"),
    LanguageItem("tg", "Tajik", "Тоҷикӣ", REGION_MIDDLE_EAST, "🇹🇯", "Cyrillic", "салом, аҳволатон чӣ хел, ҳа, не, раҳмат"),
    LanguageItem("ps", "Pashto", "پښتو", REGION_MIDDLE_EAST, "🇦🇫", "Arabic", "سلام, څنګه یاست, هو, نه, مننه"),
    LanguageItem("he", "Hebrew", "עברית", REGION_MIDDLE_EAST, "🇮🇱", "Hebrew", "שלום, מה שלומך, כן, לא, תודה, בבקשה"),
    LanguageItem("tr", "Turkish", "Türkçe", REGION_MIDDLE_EAST, "🇹🇷", "Latin", "merhaba, nasılsın, evet, hayır, teşekkür ederim"),
    LanguageItem("az", "Azerbaijani", "Azərbaycan dili", REGION_MIDDLE_EAST, "🇦🇿", "Latin", "salam, necəsən, bəli, xeyr, çox sağ olun"),
    LanguageItem("ku", "Kurdish (Kurmanji)", "Kurdî", REGION_MIDDLE_EAST, "🇹🇷", "Latin", "silav, çawa yî, erê, na, spas"),
    LanguageItem("ckb", "Kurdish (Sorani)", "سۆرانی", REGION_MIDDLE_EAST, "🇮🇶", "Arabic", "سڵاو, چۆنیت, بەڵێ, نەخێر, سوپاس"),
    LanguageItem("tk", "Turkmen", "Türkmençe", REGION_MIDDLE_EAST, "🇹🇲", "Latin", "salam, gurgunmysyňyz, hawa, ýok, sag boluň"),
    LanguageItem("uz", "Uzbek", "Oʻzbekcha", REGION_MIDDLE_EAST, "🇺🇿", "Latin", "salom, qalaysiz, ha, yoʻq, rahmat"),
    LanguageItem("kk", "Kazakh", "Қазақ тілі", REGION_MIDDLE_EAST, "🇰🇿", "Cyrillic", "сәлеметсіз бе, қалыңыз қалай, иә, жоқ, рақмет"),
    LanguageItem("ky", "Kyrgyz", "Кыргызча", REGION_MIDDLE_EAST, "🇰🇬", "Cyrillic", "саламатсызбы, кандайсыз, ооба, жок, рахмат"),
    LanguageItem("ka", "Georgian", "ქართული", REGION_MIDDLE_EAST, "🇬🇪", "Georgian", "გამარჯობა, როგორ ხარ, დიახ, არა, გმადლობთ"),
    LanguageItem("hy", "Armenian", "Հայերեն", REGION_MIDDLE_EAST, "🇦🇲", "Armenian", "բարև, ինչպե՞ս եք, այո, ոչ, շնորհակալություն"),
    LanguageItem("tt", "Tatar", "Татар теле", REGION_MIDDLE_EAST, "🇷🇺", "Cyrillic", "сәлам, хәлләр ничек, әйе, юк, рәхмәт"),
    LanguageItem("ba", "Bashkir", "Башҡорт теле", REGION_MIDDLE_EAST, "🇷🇺", "Cyrillic", "һаумыһығыҙ, хәлдәр нисек, эйе, юҡ, рәхмәт"),
    LanguageItem("cv", "Chuvash", "Чӑвашла", REGION_MIDDLE_EAST, "🇷🇺", "Cyrillic", "сывлӑх сунатпӑр, мӗнле пурӑнатӑр, ҫапла, ҫук, тавах"),
    LanguageItem("ce", "Chechen", "Нохчийн мотт", REGION_MIDDLE_EAST, "🇷🇺", "Cyrillic", "марша вогIийла, муха ду гIуллакхаш, хIаъ, хIан-хIа, баркалла"),
    LanguageItem("av", "Avar", "Авар мацӏ", REGION_MIDDLE_EAST, "🇷🇺", "Cyrillic", "ворчӏами, щиб хӏал бугеб, дица, гьечӏо, баркала"),
    LanguageItem("os", "Ossetian", "Ирон ӕвзаг", REGION_MIDDLE_EAST, "🇬🇪", "Cyrillic", "салам, куыд у, о, нӕй, бузныг"),
    LanguageItem("bal", "Balochi", "بلوچی", REGION_MIDDLE_EAST, "🇵🇰", "Arabic", "سلام, چټور ئے, ھو, نہ, منّتوار"),

    # =========================================================================
    # 5. AFRICAN LANGUAGES (35 Languages)
    # =========================================================================
    LanguageItem("sw", "Swahili", "Kiswahili", REGION_AFRICAN, "🇰🇪", "Latin", "habari, jambo, ndiyo, hapana, asante, tafadhali"),
    LanguageItem("am", "Amharic", "አማርኛ", REGION_AFRICAN, "🇪🇹", "Ge'ez", "ሰላም, እንደምን አለህ, አዎ, አይደለም, አመሰግናለሁ"),
    LanguageItem("yo", "Yoruba", "Èdè Yorùbá", REGION_AFRICAN, "🇳🇬", "Latin", "báwo ni, ṣé àlááfíà ni, bẹ́ẹ̀ni, rárá, eṣé"),
    LanguageItem("ig", "Igbo", "Asụsụ Igbo", REGION_AFRICAN, "🇳🇬", "Latin", "kedụ, kedu ka ị mere, ee, mba, daalụ"),
    LanguageItem("ha", "Hausa", "Harshen Hausa", REGION_AFRICAN, "🇳🇬", "Latin", "sannu, yaya kake, eh, a'a, na gode"),
    LanguageItem("zu", "Zulu", "isiZulu", REGION_AFRICAN, "🇿🇦", "Latin", "sawubona, unjani, yebo, cha, ngiyabonga"),
    LanguageItem("xh", "Xhosa", "isiXhosa", REGION_AFRICAN, "🇿🇦", "Latin", "molo, unjani, ewe, hayi, enkosi"),
    LanguageItem("af", "Afrikaans", "Afrikaans", REGION_AFRICAN, "🇿🇦", "Latin", "hallo, hoe gaan dit, ja, nee, dankie"),
    LanguageItem("so", "Somali", "Af-Soomaali", REGION_AFRICAN, "🇸🇴", "Latin", "nabad, see tahay, haa, maya, mahadsanid"),
    LanguageItem("om", "Oromo", "Afaan Oromoo", REGION_AFRICAN, "🇪🇹", "Latin", "akkam, nagaa dhaa, eeyyee, lakki, galatoomaa"),
    LanguageItem("ti", "Tigrinya", "ትግርኛ", REGION_AFRICAN, "🇪🇷", "Ge'ez", "ሰላም, ከመይ ኣለኻ, እወ, ኣይፋልን, የቐንየለይ"),
    LanguageItem("sn", "Shona", "chiShona", REGION_AFRICAN, "🇿🇼", "Latin", "mhoro, wakadii, hongu, kwete, maita basa"),
    LanguageItem("rw", "Kinyarwanda", "Ikinyarwanda", REGION_AFRICAN, "🇷🇼", "Latin", "muraho, amakuru, yego, oya, urakoze"),
    LanguageItem("lg", "Luganda", "Oluganda", REGION_AFRICAN, "🇺🇬", "Latin", "ki kati, oli otya, ye, nedda, weebale"),
    LanguageItem("ln", "Lingala", "Lingála", REGION_AFRICAN, "🇨🇩", "Latin", "mbote, sango nini, iyo, te, matondi"),
    LanguageItem("wo", "Wolof", "Wollof", REGION_AFRICAN, "🇸🇳", "Latin", "nanga def, mangi fi rekk, waaw, déedéet, jërëjëf"),
    LanguageItem("mg", "Malagasy", "Fiteny Malagasy", REGION_AFRICAN, "🇲🇬", "Latin", "manahoana, manao ahoana ianao, eny, tsia, misaotra"),
    LanguageItem("st", "Sesotho", "Sesotho", REGION_AFRICAN, "🇱🇸", "Latin", "lumela, o kae, e, che, ke a leboha"),
    LanguageItem("tn", "Setswana", "Setswana", REGION_AFRICAN, "🇧🇼", "Latin", "dumela, o tsogile jang, ee, nnyaa, ke a leboga"),
    LanguageItem("bm", "Bambara", "Bamanankan", REGION_AFRICAN, "🇲🇱", "Latin", "i ni sogoma, i ka kene, awò, ayi, i ni ce"),
    LanguageItem("ff", "Fulani / Fula", "Fulfulde", REGION_AFRICAN, "🇸🇳", "Latin", "no wa'i, jam tan, eey, a'a, jaaraama"),
    LanguageItem("ak", "Akan / Twi", "Twi", REGION_AFRICAN, "🇬🇭", "Latin", "ete sen, me ho ye, aane, dabi, medaase"),
    LanguageItem("ee", "Ewe", "Èʋegbe", REGION_AFRICAN, "🇬🇭", "Latin", "ndi, efoa, enu, ao, akpe"),
    LanguageItem("ki", "Kikuyu", "Gĩkũyũ", REGION_AFRICAN, "🇰🇪", "Latin", "wi mwega, ndĩ mwega, ii, aaca, ni wega"),
    LanguageItem("luo", "Luo", "Dholuo", REGION_AFRICAN, "🇰🇪", "Latin", "misawa, ing'eyo, ee, ooyo, erokamano"),
    LanguageItem("ny", "Chewa / Nyanja", "Chichewa", REGION_AFRICAN, "🇲🇼", "Latin", "moni, muli bwanji, inde, ayi, zikomo"),
    LanguageItem("rn", "Kirundi", "Ikirundi", REGION_AFRICAN, "🇧🇮", "Latin", "bwakeye, amakuru, ego, oya, urakoze"),
    LanguageItem("sg", "Sango", "Sängö", REGION_AFRICAN, "🇨🇫", "Latin", "bara ala, tongana nye, en, ôko, singila"),
    LanguageItem("ts", "Tsonga", "Xitsonga", REGION_AFRICAN, "🇿🇦", "Latin", "avuxeni, u njhani, ina, e-e, inkomu"),
    LanguageItem("ve", "Venda", "Tshivenḓa", REGION_AFRICAN, "🇿🇦", "Latin", "ndi matsheloni, vho vuwa hani, ee, hai, ndo livhuwa"),
    LanguageItem("ss", "Swati", "SiSwati", REGION_AFRICAN, "🇸🇿", "Latin", "sawubona, unjani, yebo, cha, ngiyabonga"),
    LanguageItem("nr", "Ndebele", "isiNdebele", REGION_AFRICAN, "🇿🇦", "Latin", "lotjhani, unjani, iye, awa, ngiyathokoza"),

    # =========================================================================
    # 6. AMERICAS, OCEANIA & INDIGENOUS LANGUAGES (18 Languages)
    # =========================================================================
    LanguageItem("haw", "Hawaiian", "ʻŌlelo Hawaiʻi", REGION_AMERICAS, "🌺", "Latin", "aloha, pehea ʻoe, ʻae, ʻaʻole, mahalo"),
    LanguageItem("mi", "Maori", "Te Reo Māori", REGION_AMERICAS, "🇳🇿", "Latin", "kia ora, kei te pēhea koe, āe, kāore, ngā mihi"),
    LanguageItem("sm", "Samoan", "Gagana Samoa", REGION_AMERICAS, "🇼🇸", "Latin", "tālofa, o ā mai oe, ioe, leai, faʻafetai"),
    LanguageItem("to", "Tongan", "Lea Faka-Tonga", REGION_AMERICAS, "🇹🇴", "Latin", "mālō e lelei, fēfē hake, ʻio, ʻikai, mālō"),
    LanguageItem("fj", "Fijian", "Na Vosa Vakaviti", REGION_AMERICAS, "🇫🇯", "Latin", "bula, vacava tiko, io, sega, vinaka"),
    LanguageItem("qu", "Quechua", "Runasimi", REGION_AMERICAS, "🇵🇪", "Latin", "allillanchu, allillanmi, arí, manan, sulpayki"),
    LanguageItem("gn", "Guarani", "Avañe'ẽ", REGION_AMERICAS, "🇵🇾", "Latin", "mba'éichapa, che rohayhu, heẽ, nahániri, aguyje"),
    LanguageItem("ay", "Aymara", "Aymar aru", REGION_AMERICAS, "🇧🇴", "Latin", "kamisaraki, walikiskiwa, jisa, janiwa, yuspagara"),
    LanguageItem("nah", "Nahuatl", "Nāhuatl", REGION_AMERICAS, "🇲🇽", "Latin", "niltze, queniuhqui otimotlanextili, quemeh, ahmo, tlazohcamati"),
    LanguageItem("nv", "Navajo", "Diné bizaad", REGION_AMERICAS, "🇺🇸", "Latin", "yá'át'ééh, haash yinilyé, aoo', ndaga', ahéhee'"),
    LanguageItem("chr", "Cherokee", "ᏣᎳᎩ ᎦᏬᏂᎯᏍᏗ", REGION_AMERICAS, "🇺🇸", "Cherokee", "ᎣᏏᏲ, ᏙᎯᏧ, ᎥᎥ, ᎥᏝ, ᏩᏙ"),
    LanguageItem("iu", "Inuktitut", "ᐃᓄᒃᑎᑐᑦ", REGION_AMERICAS, "🇨🇦", "Inuktitut Syllabics", "ᐊᐃ, ᖃᓄᐃᑉᐱᑦ, ᐋ, ᐋᒃᑲ, ᖁᔭᓐᓇᒦᒃ"),
    LanguageItem("kl", "Greenlandic", "Kalaallisut", REGION_AMERICAS, "🇬🇱", "Latin", "aluu, qanoq-ippit, aap, naagga, qujanaq"),
    LanguageItem("ty", "Tahitian", "Reo Tahiti", REGION_AMERICAS, "🇵🇫", "Latin", "ʻia ora na, maitaʻi, ʻē, ʻaore, māuruuru"),
    LanguageItem("tpi", "Tok Pisin", "Tok Pisin", REGION_AMERICAS, "🇵🇬", "Latin", "halo, olsem wanem, yes, nogat, tenkyu"),
    LanguageItem("ht", "Haitian Creole", "Kreyòl Ayisyen", REGION_AMERICAS, "🇭🇹", "Latin", "bonjou, kouman ou ye, wi, non, mèsi"),
    # Additional Regional & Dialectal Treasures
    LanguageItem("bns", "Bundeli", "बुन्देली", REGION_INDIAN, "🇮🇳", "Devanagari", "राम राम, का हाल है, हाँ, नहीं"),
    LanguageItem("anp", "Angika", "अंगिका", REGION_INDIAN, "🇮🇳", "Devanagari", "प्रणाम, की हाल चाल छै, हाँ, नै"),
    LanguageItem("kfa", "Kodava", "ಕೊಡವ ತಕ್ಕ್", REGION_INDIAN, "🇮🇳", "Kannada", "ನಮಸ್ಕಾರ, ಎನ್ನನೆ ಉಳ್ಳಿರ, ಹೌದು, ಇಲ್ಲೆ"),
    LanguageItem("saz", "Saurashtra", "ꢱꣃꢬꢵꢰ꣄ꢜ꣄ꢬ", REGION_INDIAN, "🇮🇳", "Saurashtra / Tamil", "ನಮಸ್ಕಾರ, ಕಸನ್ ಆಸತ್, ಹೊವ್, ನಹಿ"),
    LanguageItem("gon", "Gondi", "गोण्डी", REGION_INDIAN, "🇮🇳", "Devanagari", "सेवा जोहार, बहेल आंधी, हाँ, नहीं"),
    LanguageItem("nap", "Neapolitan", "Nnapulitano", REGION_EUROPEAN, "🇮🇹", "Latin", "ciao, comm staie, sì, no, grazie"),
    LanguageItem("pms", "Piedmontese", "Piemontèis", REGION_EUROPEAN, "🇮🇹", "Latin", "ciao, coma 't stas, sì, nò, mersì"),
    LanguageItem("fur", "Friulian", "Furlan", REGION_EUROPEAN, "🇮🇹", "Latin", "mandi, cemût stâstu, sì, no, graciis"),
    LanguageItem("csb", "Kashubian", "Kaszëbsczi", REGION_EUROPEAN, "🇵🇱", "Latin", "witôj, jak sã môsz, jo, nié, dzãkujã"),
    LanguageItem("szl", "Silesian", "Ślōnski", REGION_EUROPEAN, "🇵🇱", "Latin", "dobry dziyń, jak sie mosz, ja, niy, dinkujã"),
    LanguageItem("rue", "Rusyn", "Русиньскый", REGION_EUROPEAN, "🇺🇦", "Cyrillic", "добый день, як ся маєте, гей, нїт, дякую"),
    LanguageItem("hsn", "Xiang (Hunanese)", "湘语", REGION_ASIAN, "🇨🇳", "Simplified Han", "你好, 搞么子, 是的, 莫搞, 谢谢"),
    LanguageItem("tcy-tc", "Teochew", "潮州話", REGION_ASIAN, "🇨🇳", "Traditional Han", "汝好, 食飽未, 著, 呒著, 多謝"),
    LanguageItem("wba", "Wa", "Vax", REGION_ASIAN, "🇲🇲", "Latin", "mai pun, pa mai, ang, an ma, krax ca"),
    LanguageItem("sid", "Sidama", "Sidaamu Afoo", REGION_AFRICAN, "🇪🇹", "Latin", "keere, nagaa, ee, deeni, galatona")
]


# Fast lookup dictionaries
_BY_NAME: Dict[str, LanguageItem] = {lang.name.lower(): lang for lang in LANGUAGES_DB}
_BY_CODE: Dict[str, LanguageItem] = {lang.code.lower(): lang for lang in LANGUAGES_DB}


def get_all_languages() -> List[LanguageItem]:
    """Returns the full catalog of 200+ languages."""
    return list(LANGUAGES_DB)


def get_language_by_name(name: str) -> Optional[LanguageItem]:
    """Retrieves LanguageItem by case-insensitive English name."""
    if not name:
        return None
    return _BY_NAME.get(name.strip().lower())


def get_language_by_code(code: str) -> Optional[LanguageItem]:
    """Retrieves LanguageItem by code (e.g. 'mr', 'hi', 'en')."""
    if not code:
        return None
    return _BY_CODE.get(code.strip().lower())


def search_languages(query: str, region_filter: Optional[str] = None) -> List[LanguageItem]:
    """
    Searches languages matching query across name, native name, code, script, or region.
    Supports quick region filtering.
    """
    q = (query or "").strip().lower()
    results = []

    for lang in LANGUAGES_DB:
        if region_filter and region_filter != REGION_ALL and lang.region != region_filter:
            continue

        if not q:
            results.append(lang)
            continue

        if (
            q in lang.name.lower()
            or q in lang.native_name.lower()
            or q == lang.code.lower()
            or q in lang.region.lower()
            or q in lang.script.lower()
        ):
            results.append(lang)

    return results


# =========================================================================
# 7. FUZZY SEARCH, ALIAS DICTIONARY & SUGGESTIONS
# =========================================================================

LANGUAGE_ALIASES: Dict[str, List[str]] = {
    "marathi": ["marati", "marathe", "marath", "mrathi", "maharashtra", "मराठी"],
    "hindi": ["hindustani", "hind", "hindee", "हिन्दी", "हिंदी"],
    "sanskrit": ["samskritam", "sanskriti", "sanscrit", "संस्कृत", "संस्कृतम्"],
    "bhojpuri": ["bhojpur", "bihar", "bhojpury", "भोजपुरी"],
    "german": ["germany", "deutsch", "deutsche", "allemand", "aleman"],
    "french": ["france", "français", "francais"],
    "spanish": ["spain", "español", "espanol", "castilian", "castellano"],
    "russian": ["russia", "russan", "rusian", "русский"],
    "latin": ["latina", "latino", "rome", "roman", "latn", "ancient latin"],
    "yiddish": ["idish", "yidish", "yiddsh", "jewish", "ייִדיश", "ייִדיש"],
    "romansh": ["romance", "romanch", "rumantsch", "rhaeto-romance", "romash"],
    "romanian": ["romance", "romania", "română", "romana"],
    "italian": ["italy", "italia", "italiano"],
    "portuguese": ["portugal", "brazil", "brasil", "português", "portugues"],
    "dutch": ["netherlands", "holland", "nederlands"],
    "japanese": ["japan", "nihongo", "日本語"],
    "chinese (simplified)": ["china", "mandarin", "chinese", "zhongwen", "中文"],
    "chinese (traditional)": ["taiwan", "traditional chinese", "繁體中文"],
    "cantonese": ["canton", "hong kong", "yue", "廣東話"],
    "korean": ["korea", "hangul", "한국어"],
    "arabic (standard)": ["arab", "arabic", "arabia", "عربي", "العربية"],
    "persian / farsi": ["iran", "persia", "farsi", "فارسی"],
    "turkish": ["turkey", "türkiye", "türkçe"],
    "greek": ["greece", "hellenic", "ελληνικά"],
    "swedish": ["sweden", "svenska"],
    "norwegian": ["norway", "norsk"],
    "danish": ["denmark", "dansk"],
    "finnish": ["finland", "suomi"],
    "polish": ["poland", "polski"],
    "czech": ["czechia", "čeština"],
    "hungarian": ["hungary", "magyar"],
    "ukrainian": ["ukraine", "українська"],
    "vietnamese": ["vietnam", "tiếng việt"],
    "thai": ["thailand", "ภาษาไทย"],
    "indonesian": ["indonesia", "bahasa indonesia"],
    "tagalog / filipino": ["philippines", "filipino", "tagalog"],
    "swahili": ["kenya", "tanzania", "kiswahili"],
    "tamil": ["tamil nadu", "தமிழ்"],
    "telugu": ["andhra", "telangana", "తెలుగు"],
    "kannada": ["karnataka", "ಕನ್ನಡ"],
    "malayalam": ["kerala", "മലയാളം"],
    "bengali": ["bangla", "bengal", "bangladesh", "বাংলা"],
    "gujarati": ["gujarat", "ગુજરાતી"],
    "punjabi": ["punjab", "ਪੰਜਾਬੀ"],
    "odia": ["orissa", "odisha", "ଓଡ଼ିଆ"],
    "assamese": ["assam", "অসমীয়া"],
    "urdu": ["pakistan", "اردو"],
    "nepali": ["nepal", "नेपाली"],
    "sinhala": ["sri lanka", "සිංහල"]
}


def _calculate_match_score(query: str, lang: LanguageItem) -> float:
    """
    Computes a relevance score (0.0 to 1.0) for a query string against a LanguageItem.
    Handles exact, substring, alias, subsequence, and SequenceMatcher fuzzy similarity.
    """
    q = query.lower().strip()
    if not q:
        return 1.0

    name_lower = lang.name.lower()
    native_lower = lang.native_name.lower()
    code_lower = lang.code.lower()
    reg_lower = lang.region.lower()
    script_lower = lang.script.lower()

    # 1. Exact matches
    if q == name_lower or q == code_lower:
        return 1.0
    if q == native_lower:
        return 0.98

    # 2. Substring in primary fields
    if q in name_lower:
        return 0.90 + (len(q) / max(len(name_lower), 1)) * 0.08
    if q in native_lower or q == code_lower:
        return 0.88
    if q in reg_lower or q in script_lower:
        return 0.85

    # 3. Check alias dictionary
    aliases = LANGUAGE_ALIASES.get(name_lower, [])
    for a in aliases:
        if q == a:
            return 0.95
        if q in a or a in q:
            return 0.87
        if difflib.SequenceMatcher(None, q, a).ratio() >= 0.75:
            return 0.82

    # 4. Subsequence matching (letters in query appear in language name in order)
    it = iter(name_lower)
    if all(c in it for c in q):
        return 0.75 + (len(q) / max(len(name_lower), 1)) * 0.10

    # 5. Fuzzy ratio on name & native name
    ratio_name = difflib.SequenceMatcher(None, q, name_lower).ratio()
    if ratio_name >= 0.60:
        return ratio_name * 0.85

    ratio_native = difflib.SequenceMatcher(None, q, native_lower).ratio()
    if ratio_native >= 0.65:
        return ratio_native * 0.80

    return 0.0


def fuzzy_search_languages(
    query: str,
    region_filter: Optional[str] = None,
    threshold: float = 0.50
) -> Tuple[List[LanguageItem], List[str]]:
    """
    Performs typo-tolerant, alias-aware search across all 200+ languages.
    Returns:
      - List[LanguageItem] sorted by match score descending.
      - List[str] of suggested language names (for 'Did you mean:' chips).
    """
    q = (query or "").strip().lower()
    if not q:
        all_langs = search_languages("", region_filter)
        return all_langs, []

    scored_langs: List[Tuple[LanguageItem, float]] = []

    for lang in LANGUAGES_DB:
        if region_filter and region_filter != REGION_ALL and lang.region != region_filter:
            continue

        score = _calculate_match_score(q, lang)
        if score >= threshold:
            scored_langs.append((lang, score))

    scored_langs.sort(key=lambda x: x[1], reverse=True)
    matched_items = [item[0] for item in scored_langs]

    # Suggestions: pick top 3-4 distinct language names with high scores
    suggestions: List[str] = []
    for lang, score in scored_langs[:4]:
        if lang.name not in suggestions:
            suggestions.append(lang.name)

    return matched_items, suggestions


def format_language_prompt_instruction(selected_languages: Optional[List[str]]) -> str:
    """
    Constructs a strict, targeted AI system prompt constraint based on user's selected languages.
    Ensures Gemini accurately conditions audio recognition and outputs exclusively in the user's
    active authorized languages and scripts, preventing unselected language leaks and phonetic Romanization.
    """
    selected_set = {s.strip().lower() for s in (selected_languages or []) if s and s.strip()}

    # Case 1: Default / English Mode (0 selected or only English selected)
    # The user configured English Only (Default). Unselected languages (like Gujarati, German, Mexican Spanish,
    # Italian, Hindi, Marathi, etc.) must NOT output in foreign scripts OR Romanized transliteration;
    # they are automatically and accurately translated into meaningful, articulate English prose!
    if not selected_set or (len(selected_set) == 1 and ("english" in selected_set or "en" in selected_set)):
        return (
            "\n\n[Active Spoken Language Constraint - English Only (Default)]:\n"
            "The user has configured speech recognition for English ONLY. All unselected regional and foreign languages are strictly EXCLUDED from direct native script output.\n"
            "1. STRICT ENGLISH PROSE OUTPUT: Output MUST be exclusively in standard English prose using Latin script.\n"
            "2. MANDATORY MEANINGFUL TRANSLATION: If the speaker speaks in ANY non-English language (such as Gujarati, German, Mexican Spanish, Italian, Hindi, Marathi, Russian, French, etc.), accurately and naturally TRANSLATE the spoken thoughts directly into meaningful, articulate English sentences.\n"
            "3. ABSOLUTE PROHIBITION ON ROMANIZED TRANSLITERATION:\n"
            "   Under NO circumstances should you output phonetic Romanized transliterations (e.g. NEVER write 'majama', 'kem cho', 'kya chal raha hai', 'wie geht es dir', 'como estas', 'namaste'). You must translate the actual MEANING into proper English vocabulary (for example, translate Gujarati 'મજામાં?' into 'How are you?' or 'Are you doing well?', and Hindi 'क्या चल रहा है?' into 'What is going on?').\n"
            "4. 100% CONTENT INTEGRITY: Faithfully preserve all facts, times, dates, numbers, technical terms, and intended logic without omission or hallucination.\n"
            "5. Eliminate filler stutters and hesitation sounds ('um', 'uh', 'like') while inserting proper capitalization and punctuation."
        )

    # Case 2: Universal Mode (All 200+ languages explicitly selected)
    if "all" in selected_set or len(selected_set) >= len(LANGUAGES_DB):
        return (
            "\n\n[Active Spoken Languages - Universal Multilingual Mode (All 200+ Languages Selected)]:\n"
            "The user has explicitly activated Universal Multilingual Mode across all 200+ languages.\n"
            "1. AUTHENTIC NATIVE SCRIPT TRANSCRIPTION: Accurately detect whichever language the speaker speaks and transcribe directly into that language's authentic native script and vocabulary:\n"
            "   - Gujarati speech -> Gujarati script (ગુજરાતી, e.g. 'નમસ્તે', 'કેમ છો', 'મજામાં')\n"
            "   - German speech -> German (Deutsch) with correct umlauts (ä, ö, ü, ß)\n"
            "   - Mexican Spanish speech -> Mexican Spanish (Español) with proper punctuation (¿, ¡, ñ)\n"
            "   - Italian speech -> Italian (Italiano)\n"
            "   - Hindi speech -> Devanagari script (हिन्दी)\n"
            "   - Marathi speech -> Devanagari script (मराठी) with authentic Marathi vocabulary ('आहे', 'नाही', 'करतो', 'कसे आहात')\n"
            "   - Sanskrit speech -> Devanagari script (संस्कृतम्)\n"
            "   - Russian speech -> Cyrillic script (Русский)\n"
            "   - Japanese -> Japanese (日本語), Chinese -> Chinese (中文), Arabic -> Arabic (العربية)\n"
            "   - All other Indian, European, Asian, Middle Eastern, and African languages -> Their authentic native scripts.\n"
            "2. ABSOLUTE PROHIBITION ON ROMANIZED TRANSLITERATION:\n"
            "   NEVER output phonetic Romanized transliterations (NEVER write Hindi or Gujarati speech in English Latin alphabet, e.g. NEVER output 'Kya chal raha hai', 'kem cho', 'majama'). Always output the authentic native script of the spoken language.\n"
            "3. Clean up stutters while preserving 100% of spoken words and technical terms."
        )

    # Case 3: Specific target languages selected (e.g., 1 to 10 languages like Gujarati, German, Marathi, etc.)
    resolved_langs: List[LanguageItem] = []
    for item in selected_languages:
        lang_obj = get_language_by_name(item) or get_language_by_code(item)
        if lang_obj:
            resolved_langs.append(lang_obj)
        elif item:
            resolved_langs.append(LanguageItem(
                code=item.lower()[:3],
                name=item,
                native_name=item,
                region="Custom",
                flag="🌐",
                script="Standard"
            ))

    if not resolved_langs:
        return ""

    lang_descriptions = []
    has_marathi = any(l.name.lower() == "marathi" for l in resolved_langs)
    has_hindi = any(l.name.lower() == "hindi" for l in resolved_langs)
    has_gujarati = any(l.name.lower() == "gujarati" for l in resolved_langs)
    has_german = any(l.name.lower() == "german" for l in resolved_langs)
    has_spanish = any(l.name.lower() in ("spanish", "spanish (mexican)") for l in resolved_langs)
    has_italian = any(l.name.lower() == "italian" for l in resolved_langs)

    for l in resolved_langs:
        desc = f"• {l.name} ({l.native_name}) [Code: {l.code}, Script: {l.script}]"
        if l.sample_hints:
            desc += f" — Common Markers: {l.sample_hints}"
        lang_descriptions.append(desc)

    instructions = [
        "\n\n[ACTIVE SPOKEN LANGUAGES CONSTRAINT - STRICT SELECTION ENFORCEMENT]:",
        "The user has explicitly authorized ONLY the following active spoken language(s):",
        "\n".join(lang_descriptions),
        "\nCRITICAL SELECTION ENFORCEMENT RULES:",
        "1. STRICT AUTHORIZED OUTPUT: Output is permitted ONLY in the authorized language(s) listed above.",
        "2. AUTHENTIC NATIVE SCRIPT: When the speaker speaks in an authorized language, transcribe 100% faithfully into its authentic native script (e.g. Gujarati script for Gujarati, Devanagari for Marathi/Hindi, German with umlauts, Spanish with punctuation ¿/¡, Italian with proper grammar).",
        "3. UNSELECTED LANGUAGES TRANSLATION: If the speaker speaks in any language NOT in the authorized list above, do NOT output in that unselected language's script. Accurately translate the spoken thoughts into English.",
        "4. ABSOLUTE PROHIBITION ON ROMANIZED TRANSLITERATION: Under NO circumstances should you output phonetic Romanized transliterations (e.g. NEVER write 'majama', 'kem cho', 'kya chal raha hai'). Either transcribe in authentic native script if authorized, or translate into proper English words.",
    ]

    # Specific phonetic disambiguation for Marathi vs Hindi
    if has_marathi and not has_hindi:
        instructions.append(
            "5. MARATHI AUTHORIZED / HINDI EXCLUDED: The user selected Marathi, but did NOT select Hindi. "
            "If the speaker speaks Marathi, transcribe in authentic Marathi Devanagari ('आहे', 'नाही', 'करतो', 'झाले', 'कसे आहात'). "
            "If the speaker speaks Hindi, Hindi is UNSELECTED: translate it into English."
        )
    elif has_hindi and not has_marathi:
        instructions.append(
            "5. HINDI AUTHORIZED / MARATHI EXCLUDED: The user selected Hindi, but did NOT select Marathi. "
            "If the speaker speaks Hindi, transcribe in authentic Hindi Devanagari ('है', 'नहीं', 'कर रहा है', 'कैसे हैं'). "
            "If the speaker speaks Marathi, Marathi is UNSELECTED: translate it into English."
        )
    elif has_marathi and has_hindi:
        instructions.append(
            "5. BOTH MARATHI & HINDI AUTHORIZED: Distinguish Marathi (मराठी) and Hindi (हिन्दी) grammar carefully. "
            "Transcribe Marathi speech with Marathi vocabulary ('आहे', 'नाही', 'करतो') and Hindi speech with Hindi vocabulary ('है', 'नहीं', 'करता')."
        )

    instructions.append("6. TECHNICAL JARGON & CODE-SWITCHING: When regional speech is mixed with English technical terms ('database', 'localhost', 'dataset', 'API', 'code'), preserve the English technical terms in Latin script.")
    instructions.append("7. Eliminate verbal stutters and pauses while preserving 100% of the authentic spoken content and logic.")

    return "\n".join(instructions)
