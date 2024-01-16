import os
from dotenv import load_dotenv
load_dotenv()
import telebot
import requests
from googletrans import Translator
import re

choose_language_txt : str = "Choose a language, or reply with a country-flag emoji:"
please_reply_txt : str = "Please reply to this message with the text"

BOT_API = os.getenv("API_KEY2")
bot = telebot.TeleBot(str(BOT_API))
gtrans = Translator()
translation = gtrans.translate(dest='es', text=None)


def get_language_code(country_code):
    try:
        url = f"https://restcountries.com/v2/alpha/{country_code}"
        response = requests.get(url)
        data = response.json()

        if "languages" in data:
            primary_language_code = data["languages"][0]["iso639_1"]
            return primary_language_code
    except Exception as e:
        print(f"Error: {e}")
        pass

    return None

def normalize_code(code:str):
    if code:
        try:
            return ''.join(chr(ord(char) - ord('🇦') + ord('A')) for char in code)
        except:
            pass
    return None

def extract_lang_codes(input_string):
    hit = False
    first_word = input_string.split()[0]
    if len(first_word) < 2:
        hit = False
        return None, None, hit
    if get_language_code(normalize_code(first_word[0]+first_word[1])):
        if len(first_word) <= 2:
            to_lang_code = first_word[0]+first_word[1]
            to_lang = get_language_code(normalize_code(to_lang_code))
            hit = True
            return None, to_lang, hit
        elif len(first_word) <= 4:
            from_lang_code = first_word[0]+first_word[1]
            from_lang =  get_language_code(normalize_code(from_lang_code))
            print("from lang at line 56:", from_lang)
            to_lang_code = first_word[2]+first_word[3]
            to_lang = get_language_code(normalize_code(to_lang_code))
            hit = True
            return from_lang, to_lang, hit
    else:
        hit = False
        return None, None, hit

@bot.message_handler(commands=["start"])
def more(message):
    bot.send_message(message.chat.id,"You can use the country-flag emojis to translate stuff!\n\nExamples:\n\n🇬🇧 [text] -> This will translate any input text to English\n\n🇬🇧 🇪🇸 [text] -> This will translate from English to Spanish\n\nOr you can just send a flag emoji then reply with the text that you want to translate.\n\nYou can also reply to a message with a country-flag emoji to instantly translate it that language!\n")

@bot.message_handler(commands=["help"])
def help(message):
    bot.send_message(message.chat.id, bot.get_my_description().description)

def contains_country_flag_emoji(text):
    # Define a regular expression pattern for country flag emojis
    country_flag_pattern = re.compile(r'[\U0001F1E6-\U0001F1FF]{2}')

    # Use re.search() to check if the pattern is found in the text
    return bool(country_flag_pattern.search(text))

def check_two_flags(message):
    # if it's emoji and has language code
    print('hi')
    msg_parts = message.text.split(None, 1) if message.text else message.split(None, 1)
    from_lang = None
    print("from lang at line 85:", from_lang)
    txt_to_trans = msg_parts[1] if len(msg_parts) > 1 else None
    lang_codes_result = extract_lang_codes(msg_parts[0])

    if contains_country_flag_emoji(msg_parts[0]): # has country flag emoji
        if lang_codes_result[1]: # has to_lang aka is flag
            print('found valid language code')
            print(lang_codes_result[0])
            pass
        else:
            print('no valid language code')
            return
    else:
        print('not a country flag emoji')
        return

    if lang_codes_result:
        if lang_codes_result[0] is not None:
            from_lang = lang_codes_result[0]
            print("from lang at line 104:", from_lang)
        else:
            if message.reply_to_message is not None:
                if txt_to_trans and (message.reply_to_message.text not in choose_language_txt or message.reply_to_message.text in please_reply_txt):
                    from_lang = gtrans.detect(txt_to_trans).lang
                    if isinstance(from_lang, list) and any(isinstance(item, str) for item in from_lang): # if this is a list and any of the items are str items not chr items
                        from_lang = from_lang[0]
                    print("from lang at line 109:", from_lang)
            else:
                from_lang = None
                print("from lang at line 112:", from_lang)
        to_lang = lang_codes_result[1]
        print('there')
        return True, from_lang, to_lang, txt_to_trans
    elif lang_codes_result is None:
        print('false')
        return False


@bot.message_handler(func=check_two_flags)
def translate_two_flags(message):
    print("trans_two_flags")

    if message.reply_to_message is not None:
        if extract_lang_codes(message.text)[2] is False and (message.reply_to_message.text == choose_language_txt):
            bot.reply_to(message, "Language code not found. Sorry!")
            return
    try:
        check_result = check_two_flags(message)
        if check_result[0]:
            from_lang, to_lang, text_to_trans = check_result[1], check_result[2], check_result[3]
            print("found from,to, and txt_to_trans")
            try:
                if message.reply_to_message is not None and (message.reply_to_message.text not in choose_language_txt or message.reply_to_message.text in please_reply_txt):
                    print("this is a reply, translating text")
                    print(message.reply_to_message.text)
                    if from_lang is None:
                        from_lang = gtrans.detect(message.reply_to_message.text).lang
                        if isinstance(from_lang, list) and any(isinstance(item, str) for item in from_lang): # if this is a list and any of the items are str items not chr items
                            from_lang = from_lang[0]
                        print("from lang at line 139:", from_lang)
                    print(from_lang)
                    print(to_lang)
                    translation = gtrans.translate(text=message.reply_to_message.text, dest=to_lang, src=from_lang).text
                    print(translation)
                    bot.reply_to(message.reply_to_message, f"{message.from_user.first_name}, here's your translation from {from_lang.upper()} to {to_lang.upper()}:\n\n```\n{translation}```",parse_mode='MarkdownV2')
                    bot.delete_message(message.chat.id, message.message_id)
                    return
                else:
                    print('we here')
                    if text_to_trans:
                        print("found text to trans")
                        if from_lang is None:
                            from_lang = gtrans.detect(message.text).lang
                            if isinstance(from_lang, list) and any(isinstance(item, str) for item in from_lang): # if this is a list and any of the items are str items not chr items
                                from_lang = from_lang[0]
                            print("from lang at line 153:", from_lang)
                        print("from lang at line 160:", from_lang)
                        translation = gtrans.translate(text=text_to_trans, dest=to_lang, src=from_lang).text
                        bot.reply_to(message, f"{message.from_user.first_name}, here's your translation from {from_lang.upper()} to {to_lang.upper()}:\n\n```\n{translation}```",parse_mode='MarkdownV2')
                    else:
                        bot_reply_msg = bot.send_message(message.chat.id, f"{message.from_user.first_name}, Please reply to this message with the text you wish to translate to {to_lang.upper()}", reply_markup=telebot.types.ForceReply(selective=True), reply_to_message_id=message.message_id)
                        #bot_reply_msg = bot.reply_to(message, f"{message.from_user.first_name}, Please reply to this message with the text you wish to translate to {to_lang.upper()}")
                        flag_msg = message
                        bot.register_for_reply(bot_reply_msg, handle_trans_reply, to_lang, flag_msg, from_lang)
            except:
                # no reply message, or reply message is not a bot reply
                print('this?')
                pass
        else:
            print("HERE?")
            pass
    except:
        print('this')
        pass

# ANY - ES (commands are: *es, *espanol/español, *سباني|اسباني) EASIESST IS: es
def check_any_es(message):
    return message.text.split()[0].replace(message.text[0],"").lower() in ("espanol", "español", "spanish", "es", "سباني", "اسباني") and not message.text.lower().split()[0][0].isalpha() or message.text.lower().split()[0] == "🇪🇸"
@bot.message_handler(func=check_any_es)
def translate_any_es(message):
    to_lang = 'es'
    text_to_trans = " ".join(message.text.split()[1:])
    translation = gtrans.translate(text=text_to_trans, dest='es').text
    try:
        if message.text.split()[1]:
            from_lang = gtrans.detect(text_to_trans).lang
            if isinstance(from_lang, list) and any(isinstance(item, str) for item in from_lang): # if this is a list and any of the items are str items not chr items
                from_lang = from_lang[0]
            print("from lang at line 179:", from_lang)
            print(from_lang)
            match from_lang:
                case "en":
                    bot.reply_to(message,  f"{message.from_user.first_name}, here's your translation from 🇬🇧 to 🇪🇸:\n\n```\n{translation}```",parse_mode='MarkdownV2')
                    return
                case "ar":
                    bot.reply_to(message,  f"{message.from_user.first_name}, here's your translation from 🇪🇬 to 🇪🇸:\n\n```\n{translation}```",parse_mode='MarkdownV2')
                    return
            bot.reply_to(message,  f"{message.from_user.first_name}, here's your translation from {from_lang.upper()} to ES:\n\n```\n{translation}```",parse_mode='MarkdownV2')

    except:
        bot_reply_msg = bot.send_message(message.chat.id, f"{message.from_user.first_name}, Please reply to this message with the text you wish to translate to {to_lang.upper()}", reply_markup=telebot.types.ForceReply(selective=True), reply_to_message_id=message.message_id)
        bot.register_for_reply(bot_reply_msg, handle_trans_reply, to_lang, flag_msg=None, from_lang=None)


# ANY - EN (commands are: en, english, نجليزي|انجليزي) EASIEST IS: en
def check_any_en(message):
    return message.text.split()[0].replace(message.text[0],"").lower() in ("en", "english", "انجليزي", "نجليزي", "ن", "🇬🇧") and not message.text.lower().split()[0][0].isalpha() or message.text.lower().split()[0] == "🇬🇧"
@bot.message_handler(func=check_any_en)
def translate_any_en(message):
    to_lang = 'en'
    text_to_trans = " ".join(message.text.split()[1:])
    translation = gtrans.translate(text=text_to_trans, dest='en').text
    try:
        if message.text.split()[1]:
            from_lang = gtrans.detect(text_to_trans).lang
            if isinstance(from_lang, list) and any(isinstance(item, str) for item in from_lang): # if this is a list and any of the items are str items not chr items
                from_lang = from_lang[0]
            print("from lang at line 207:", from_lang)
            match from_lang:
                case "es":
                    bot.reply_to(message,  f"{message.from_user.first_name}, here's your translation from 🇪🇸 to 🇬🇧:\n\n```\n{translation}```",parse_mode='MarkdownV2')
                    return
                case "ar":
                    bot.reply_to(message,  f"{message.from_user.first_name}, here's your translation from 🇪🇬 to 🇬🇧:\n\n```\n{translation}```",parse_mode='MarkdownV2')
                    return
            bot.reply_to(message,  f"{message.from_user.first_name}, here's your translation from {from_lang.upper()} to EN:\n\n```\n{translation}```",parse_mode='MarkdownV2')

    except:
        bot_reply_msg = bot.send_message(message.chat.id, f"{message.from_user.first_name}, Please reply to this message with the text you wish to translate to {to_lang.upper()}", reply_markup=telebot.types.ForceReply(selective=True), reply_to_message_id=message.message_id)
        bot.register_for_reply(bot_reply_msg, handle_trans_reply, to_lang, flag_msg=None, from_lang=None)


# ANY - AR (commands are: *ar, *arabic) EASIEST IS: *ar
def check_any_ar(message):
    return message.text.split()[0].replace(message.text[0],"").lower() in ("ar", "arabic", "🇪🇬") and not message.text.lower().split()[0][0].isalpha() or message.text.lower().split()[0] in ("🇪🇬")
@bot.message_handler(func=check_any_ar)
def translate_any_ar(message):
    text_to_trans = " ".join(message.text.split()[1:])
    to_lang = 'ar'
    try:
        if message.text.split()[1]:
            from_lang = gtrans.detect(text_to_trans).lang
            if isinstance(from_lang, list) and any(isinstance(item, str) for item in from_lang): # if this is a list and any of the items are str items not chr items
                from_lang = from_lang[0]
            print("from lang at line 232:", from_lang)
            translation = gtrans.translate(text=text_to_trans, dest='ar').text
            bot.reply_to(message,  f"{message.from_user.first_name}, here's your translation from {from_lang.upper()} to AR:\n\n```\n{translation}```",parse_mode='MarkdownV2')

    except:
        bot_reply_msg = bot.send_message(message.chat.id, f"{message.from_user.first_name}, Please reply to this message with the text you wish to translate to {to_lang.upper()}", reply_markup=telebot.types.ForceReply(selective=True), reply_to_message_id=message.message_id)
        bot.register_for_reply(bot_reply_msg, handle_trans_reply, to_lang, flag_msg=None, from_lang=None)

# EN - ES (commands are: en-es, *enes, *espanol) EASIEST IS: /enes
def check_en_es(message):
    return message.text.lower().split()[0] in ("en-es", "🇬🇧 🇪🇸", "🇬🇧🇪🇸") or (message.text.split()[0].replace(message.text[0],"").lower() in ("en-es", "enes") and not message.text.lower().split()[0][0].isalpha())
@bot.message_handler(func=check_en_es)
def translate_en_es(message):
    to_lang = 'es'
    try:
        if message.text.split()[1]:
            text_to_trans = " ".join(message.text.split()[1:])
            translation = gtrans.translate(text=text_to_trans, dest='es',src='en').text
            bot.reply_to(message,  f"{message.from_user.first_name}, here's your translation from 🇬🇧 to 🇪🇸:\n\n```\n{translation}```",parse_mode='MarkdownV2')

    except:
        #bot.reply_to(message, "Please input English text to translate it into Spanish")
        bot_reply_msg = bot.send_message(message.chat.id, f"{message.from_user.first_name}, Please reply to this message with the English text you wish to translate to {to_lang.upper()}", reply_markup=telebot.types.ForceReply(selective=True), reply_to_message_id=message.message_id)
        flag_msg = message
        bot.register_for_reply(bot_reply_msg, handle_trans_reply, to_lang, flag_msg, from_lang = 'en')


# ES - EN (commands are: es-en, *esen, *ingles) EASIEST IS: ingles
def check_es_en(message):
    return message.text.lower().split()[0] in ("es-en", "🇪🇸 🇬🇧", "🇪🇸🇬🇧") or (message.text.split()[0].replace(message.text[0],"").lower() in ("es-en", "esen", "ingles") and not message.text.lower().split()[0][0].isalpha())
@bot.message_handler(func=check_es_en)
def translate_es_en(message):
    to_lang = 'en'
    try:
        if message.text.split()[1]:
            text_to_trans = " ".join(message.text.split()[1:])
            translation = gtrans.translate(text=text_to_trans, dest='en',src='es').text
            bot.reply_to(message,  f"{message.from_user.first_name}, here's your translation from 🇪🇸 to 🇬🇧:\n\n```\n{translation}```",parse_mode='MarkdownV2')

    except:
        #bot.reply_to(message, "Please input Spanish text to translate it into English")
        bot_reply_msg = bot.send_message(message.chat.id, f"{message.from_user.first_name}, Please reply to this message with the Spanish text you wish to translate to {to_lang.upper()}", reply_markup=telebot.types.ForceReply(selective=True), reply_to_message_id=message.message_id)
        flag_msg = message
        bot.register_for_reply(bot_reply_msg, handle_trans_reply, to_lang, flag_msg, from_lang='es')


# ES - AR (commands are: es-ar, *arabica/arábica, *esar) EASIEST IS: arabica
def check_es_ar(message):
    return message.text.lower().split()[0] in ("es-ar", "🇪🇸 🇪🇬", "🇪🇸🇪🇬") or (message.text.split()[0].replace(message.text[0],"").lower() in ("esar", "arabica", "arábica") and not message.text.lower().split()[0][0].isalpha())
@bot.message_handler(func=check_es_ar)
def translate_es_ar(message):
    to_lang = 'ar'
    try:
        if message.text.split()[1]:
            text_to_trans = " ".join(message.text.split()[1:])
            translation = gtrans.translate(text=text_to_trans, dest='ar',src='es').text
            print("here")
            bot.reply_to(message,  f"{message.from_user.first_name}, here's your translation from 🇪🇸 to 🇪🇬:\n\n```\n{translation}```",parse_mode='MarkdownV2')

    except:
        #bot.reply_to(message, "Please input Spanish text to translate it into Arabic")
        bot_reply_msg = bot.send_message(message.chat.id, f"{message.from_user.first_name}, Please reply to this message with the Spanish text you wish to translate to {to_lang.upper()}", reply_markup=telebot.types.ForceReply(selective=True), reply_to_message_id=message.message_id)
        flag_msg = message
        bot.register_for_reply(bot_reply_msg, handle_trans_reply, to_lang, flag_msg, from_lang='es')


# AR - ES (commands are: ar-es, *ares, سباني, اسباني, س) EASIEST IS: !س or !سباني
def check_ar_es(message):
    return message.text.lower().split()[0] in ("ar-es", "🇪🇬 🇪🇸", "🇪🇬🇪🇸") or (message.text.split()[0].replace(message.text[0],"").lower() in ("ares", "سباني", "اسباني", "س") and not message.text.lower().split()[0][0].isalpha())
@bot.message_handler(func=check_ar_es)
def translate_ar_es(message):
    from_lang = 'ar'
    print("from lang at line 304:", from_lang)
    to_lang = 'es'
    try:
        if message.text.split()[1]:
            text_to_trans = " ".join(message.text.split()[1:])
            translation = gtrans.translate(text=text_to_trans, dest=from_lang,src=to_lang).text
            bot.reply_to(message,  f"{message.from_user.first_name}, here's your translation from 🇪🇬 to 🇪🇸:\n\n```\n{translation}```",parse_mode='MarkdownV2')

    except:
        #bot.reply_to(message, "معلش إكتب حاجة بالعربي عشان تترجمها اساني 😊")
        bot_reply_msg = bot.send_message(message.chat.id, f"{message.from_user.first_name}, Please reply to this message with the Arabic text you wish to translate to {to_lang.upper()}", reply_markup=telebot.types.ForceReply(selective=True), reply_to_message_id=message.message_id)
        flag_msg = message
        bot.register_for_reply(bot_reply_msg, handle_trans_reply, to_lang, flag_msg, from_lang)


# AR - EN (commands are: ar-en, *aren, نجليزي, انجليزي, ن) EASIEST IS: !نجليزي
def check_ar_en(message):
    return message.text.lower().split()[0] in ("ar-en", "🇪🇬 🇬🇧", "🇪🇬🇬🇧") or (message.text.split()[0].replace(message.text[0],"").lower() in ("aren", "ن", "انجليزي", "نجليزي") and not message.text.lower().split()[0][0].isalpha())
@bot.message_handler(func=check_ar_en)
def translate_ar_en(message):
    from_lang = 'ar'
    print("from lang at line 325:", from_lang)
    to_lang = 'en'
    try:
        if message.text.split()[1]:
            text_to_trans = " ".join(message.text.split()[1:])
            translation = gtrans.translate(text=text_to_trans, dest=from_lang,src=to_lang).text
            bot.reply_to(message,  f"{message.from_user.first_name}, here's your translation from 🇪🇬 to 🇬🇧:\n\n```\n{translation}```",parse_mode='MarkdownV2')

    except:
        #bot.reply_to(message, "معلش إكتب حاجة بالعربي عشان تترجمها انجليزي 😊")
        bot_reply_msg = bot.send_message(message.chat.id, f"{message.from_user.first_name}, Please reply to this message with the Arabic text you wish to translate to {to_lang.upper()}", reply_markup=telebot.types.ForceReply(selective=True), reply_to_message_id=message.message_id)
        flag_msg = message
        bot.register_for_reply(bot_reply_msg, handle_trans_reply, to_lang, flag_msg, from_lang)


# EN - AR (commands are: en-ar, *enar) EASIEST IS: *enar
def check_en_ar(message):
    return (message.text.lower().split()[0] in ("en-ar", "🇬🇧 🇪🇬", "🇬🇧🇪🇬") ) or ( message.text.split()[0].replace(message.text[0],"").lower() == "enar" and not message.text.lower().split()[0][0].isalpha() )
@bot.message_handler(func=check_en_ar)
def translate_en_ar(message):
    from_lang = 'en'
    print("from lang at line 346:", from_lang)
    to_lang = 'ar'
    try:
        if message.text.split()[1]:
            text_to_trans = " ".join(message.text.split()[1:])
            translation = gtrans.translate(text=text_to_trans, dest=from_lang,src=to_lang).text
            bot.reply_to(message,  f"{message.from_user.first_name}, here's your translation from 🇬🇧 to 🇪🇬:\n\n```\n{translation}```",parse_mode='MarkdownV2')

    except:
        #bot.reply_to(message, "Please input English text to translate into Arabic 😊")
        bot_reply_msg = bot.send_message(message.chat.id, f"{message.from_user.first_name}, Please reply to this message with the English text you wish to translate to {to_lang.upper()}", reply_markup=telebot.types.ForceReply(selective=True), reply_to_message_id=message.message_id)
        flag_msg = message
        bot.register_for_reply(bot_reply_msg, handle_trans_reply, to_lang, flag_msg, from_lang)

def gen_markup():
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    btns = {
        "es_btn" : telebot.types.InlineKeyboardButton("🇪🇸", callback_data="cb_es"),
        "en_btn" : telebot.types.InlineKeyboardButton("🇬🇧", callback_data="cb_en"),
        "ar_btn" : telebot.types.InlineKeyboardButton("🇪🇬", callback_data="cb_ar"),
        "ja_btn" : telebot.types.InlineKeyboardButton("🇯🇵", callback_data="cb_ja"),
        "ko_btn" : telebot.types.InlineKeyboardButton("🇰🇷", callback_data="cb_ko"),
        "fr_btn" : telebot.types.InlineKeyboardButton("🇫🇷", callback_data="cb_fr"),
    }

    for e in btns:
        markup.add(btns[e])
    return markup

@bot.message_handler(func=lambda message: message.text.split()[0].replace(message.text[0],"").lower() in ("t", "translate", "ت") and not message.text.lower().split()[0][0].isalpha() or message.text.lower().split()[0] == "🇪🇸")
def bot_reply_choose_lang(message):
    print(message.text)
    bot.reply_to(message, choose_language_txt, reply_markup=gen_markup())

@bot.callback_query_handler(lambda call: True)
def callback_query(call):
    text_to_trans = " ".join(call.message.reply_to_message.text.split()[1:])
    if text_to_trans:
        from_lang = gtrans.detect(text_to_trans).lang
        if isinstance(from_lang, list) and any(isinstance(item, str) for item in from_lang): # if this is a list and any of the items are str items not chr items
            from_lang = from_lang[0]
        print("from lang at line 385:", from_lang)
    to_lang = "es" #
    match call.data:
        case "cb_es":
            translation = gtrans.translate(text=text_to_trans, dest='es').text
            to_lang = "es"
        case "cb_en":
            translation = gtrans.translate(text=text_to_trans, dest='en').text
            to_lang = "en"
        case "cb_ar":
            translation = gtrans.translate(text=text_to_trans, dest='ar').text
            to_lang = "ar"
        case "cb_ja":
            translation = gtrans.translate(text=text_to_trans, dest='ja').text
            to_lang = "ja"
        case "cb_ko":
            translation = gtrans.translate(text=text_to_trans, dest='ko').text
            to_lang = "ko"
        case "cb_fr":
            translation = gtrans.translate(text=text_to_trans, dest='fr').text
            to_lang = "fr"
    if call.message.reply_to_message.text.split()[0].replace(call.message.reply_to_message.text[0],"").lower() in ("t", "translate", "ت") and len(call.message.reply_to_message.text.split()) > 1:
        bot.reply_to(call.message.reply_to_message, f"{call.message.reply_to_message.from_user.first_name}, here's your translation from {from_lang.upper()} to {to_lang.upper()}:\n\n```\n{translation}```",parse_mode='MarkdownV2')
        bot.delete_message(call.message.chat.id, call.message.id)
    else:
        bot_reply_msg = bot.send_message(call.message.chat.id, f"{call.message.reply_to_message.from_user.first_name}, Reply to this message with the text you wish to translate to {to_lang.upper()}", reply_markup=telebot.types.ForceReply(selective=True), reply_to_message_id=call.message.reply_to_message.message_id)
        #bot_reply_msg = bot.reply_to(call.message.reply_to_message, f"{call.message.reply_to_message.from_user.first_name}, Reply to this message with the text you wish to translate to {to_lang.upper()}")
        bot.delete_message(call.message.chat.id, call.message.id)
        bot.delete_message(call.message.reply_to_message.chat.id, call.message.reply_to_message.message_id)
        bot.register_for_reply(bot_reply_msg, handle_trans_reply, to_lang, flag_msg=None, from_lang=None)


def handle_trans_reply(message, to_lang, flag_msg, from_lang):
    print("entered handle trans reply")
    if message.reply_to_message != None:
        text_to_trans = message.text
        if from_lang is None:
            from_lang = gtrans.detect(text_to_trans).lang
            if isinstance(from_lang, list) and any(isinstance(item, str) for item in from_lang): # if this is a list and any of the items are str items not chr items
                from_lang = from_lang[0]
            print("from lang at line 423:", from_lang)
        translation = gtrans.translate(text=text_to_trans, dest=to_lang, src=from_lang).text
        bot.reply_to(message, f"{message.from_user.first_name}, here's your translation from {from_lang.upper()} to {to_lang.upper()}:\n\n```\n{translation}```",parse_mode='MarkdownV2')
        bot.delete_message(message.chat.id, message.reply_to_message.message_id)
        if flag_msg:
            if flag_msg.reply_to_message: # choose a language text
                bot.delete_message(message.chat.id, flag_msg.reply_to_message.message_id)
            bot.delete_message(message.chat.id, flag_msg.message_id)



bot.polling()