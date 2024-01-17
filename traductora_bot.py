import os
from dotenv import load_dotenv
load_dotenv()
import telebot
import requests
from googletrans import Translator
import re
import speech_recognition as sr
import io
from pydub import AudioSegment
from pydub.playback import play
import azure.cognitiveservices.speech as speechsdk
from babel import Locale


global global_from_lang, global_to_lang

choose_language_txt : str = "Choose a language, or reply with a country-flag emoji to set the destination language:"
please_reply_txt : str = "reply to this message with the text"

BOT_API = os.getenv("API_KEY2")
bot = telebot.TeleBot(str(BOT_API))
gtrans = Translator()
translation = gtrans.translate(dest='es', text=None)

def get_locale_from_country_code(country_code):
    try:
        # Create a Locale object using the country code
        locale = Locale.parse(f"und_{country_code}")

        # Get the full locale code
        full_locale = str(locale)

        return full_locale.replace('_','-')
    except ValueError:
        # Handle the case where an invalid country code is provided
        return None

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
            print("COULDN'T NORMALIZE CODE")
    return None

def extract_lang_codes(input_string):
    print("EXTRACTING LANG CODES")
    hit = False
    first_word = input_string.split()[0]
    if len(first_word) < 2:
        hit = False
        return None, None, hit, None, None
    try:
        if get_language_code(normalize_code(first_word[0]+first_word[1])):
            if len(first_word) <= 2:
                to_lang_code = first_word[0]+first_word[1]
                to_lang_code_normalized = normalize_code(to_lang_code)
                to_lang = get_language_code(normalize_code(to_lang_code))
                hit = True
                print("from_lang_normalized is:", to_lang_code_normalized)
                return None, to_lang, hit, None, to_lang_code_normalized
            
            elif len(first_word) <= 4:
                from_lang_code = first_word[0]+first_word[1]
                from_lang_code_normalized = normalize_code(from_lang_code)
                from_lang =  get_language_code(normalize_code(from_lang_code))
                print("from lang at line 56:", from_lang)
                to_lang_code = first_word[2]+first_word[3]
                to_lang_code_normalized = normalize_code(to_lang_code)
                to_lang = get_language_code(normalize_code(to_lang_code))
                hit = True
                print("from_lang_normalized is:", from_lang_code_normalized)
                print("to_lang_normalized is:", to_lang_code_normalized)
                return from_lang, to_lang, hit, from_lang_code_normalized, to_lang_code_normalized
        else:
            hit = False
            return None, None, hit, None, None
    except:
        print('ERROR GETTING LANGUAGE CODE')

@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(message.chat.id,"You can use the country-flag emojis to translate stuff!\n\nExamples:\n🇬🇧 [text] -> This will translate any input text to English\n\n🇬🇧 🇪🇸 [text] -> This will translate from English to Spanish\n\nOr you can just send a flag emoji then reply with the text that you want to translate.\n\nYou can also reply to a message with a country-flag emoji to instantly translate it to that language! _Try it out by replying to this message with the Spain country-flag emoji_ 🇪🇸.\n\n`You can still use the two-emoji format when replying to force the source language instead of having the translation API detect it.`\n",parse_mode="Markdown")

@bot.message_handler(commands=["help"])
def help(message):
    bot.send_message(message.chat.id, bot.get_my_description().description)

def contains_country_flag_emoji(text):
    # Define a regular expression pattern for country flag emojis
    country_flag_pattern = re.compile(r'[\U0001F1E6-\U0001F1FF]{2}')

    # Use re.search() to check if the pattern is found in the text
    return bool(country_flag_pattern.search(text))

def check_flags(message):
    print('hi')
    msg_parts = message.text.split(None, 1) if message.text else message.split(None, 1)
    from_lang = None
    from_locale=None
    to_locale = None
    print("from lang at line 85:", from_lang)
    txt_to_trans = msg_parts[1] if len(msg_parts) > 1 else None
    lang_codes_result = extract_lang_codes(msg_parts[0])
    print("LOOK FOR THIS",lang_codes_result)
    try:
        from_locale = get_locale_from_country_code(lang_codes_result[3])
        print("at line 119, from_locale is: ", from_locale)
    except:
        print('ERROR GETTING FROM_LOCALE')

    try:
        to_locale = get_locale_from_country_code(lang_codes_result[4])
        print("at line 119, to_locale is: ", to_locale)
    except:
        print('ERROR GETTING TO_LOCALE')
    
    if lang_codes_result:
        if message.reply_to_message and message.reply_to_message.content_type == "voice":
            print("VOICE?")
            translate_voice(message.reply_to_message, lang_codes_result[0], lang_codes_result[1], from_locale, to_locale)
            return
        
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
        return True, from_lang, to_lang, txt_to_trans, from_locale, to_locale
    elif lang_codes_result is None:
        print('false')
        return False


@bot.message_handler(func=check_flags)
def translate_two_flags(message):
    print("trans_two_flags")

    if message.reply_to_message is not None:
        if extract_lang_codes(message.text)[2] is False and (message.reply_to_message.text == choose_language_txt):
            bot.reply_to(message, "Language code not found. Sorry!")
            return
        elif message.reply_to_message.content_type == "voice":
            print("reply_message is a voice")
            translate_voice(message.reply_to_message, from_lang, to_lang, from_locale, to_locale)
            return
    try:
        check_result = check_flags(message)
        print("got check results")
        if check_result[0]:
            print("check results index 0 is true")
            from_lang, to_lang, text_to_trans, from_locale, to_locale = check_result[1], check_result[2], check_result[3], check_result[4], check_result[5]
            print("got from, to, and txt_to_trans, from_locale, to_locale")
            print(from_locale, to_locale)
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
                    bot.reply_to(message.reply_to_message, f"{message.from_user.first_name}, here's your translation from {from_lang.upper()} to {to_lang.upper()}:\n\n```\n{translation}```",parse_mode='Markdown')
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
                        bot.reply_to(message, f"{message.from_user.first_name}, here's your translation from {from_lang.upper()} to {to_lang.upper()}:\n\n```\n{translation}```",parse_mode='Markdown')
                    else:
                        print("223")
                        bot_reply_msg = bot.send_message(message.chat.id, f"{message.from_user.first_name}, please reply to this message with the text or voice note you wish to translate to {to_lang.upper()}", reply_markup=telebot.types.ForceReply(selective=True), reply_to_message_id=message.message_id)
                        #bot_reply_msg = bot.reply_to(message, f"{message.from_user.first_name}, please reply to this message with the text or voice note you wish to translate to {to_lang.upper()}")
                        flag_msg = message
                        bot.register_for_reply(bot_reply_msg, handle_trans_reply, to_lang, flag_msg, from_lang, from_locale, to_locale)
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
    from_lang = None
    to_lang = 'es'
    try:
        text_to_trans = " ".join(message.text.split()[1:])
        translation = gtrans.translate(text=text_to_trans, dest='es').text
        print(message.text.split()[0])
        if message.content_type != "voice" and message.content_type == 'text':
            try:
                if message.text.split()[1]:
                    print('249')
                    from_lang = gtrans.detect(text_to_trans).lang
                    try:
                        if isinstance(from_lang, list) and any(isinstance(item, str) for item in from_lang): # if this is a list and any of the items are str items not chr items
                            from_lang = from_lang[0]
                    except: pass
                    print("from lang at line 179:", from_lang)
                    print(from_lang)
                    match from_lang:
                        case "en":
                            bot.reply_to(message,  f"{message.from_user.first_name}, here's your translation from 🇬🇧 to 🇪🇸:\n\n```\n{translation}```",parse_mode='Markdown')
                            return
                        case "ar":
                            bot.reply_to(message,  f"{message.from_user.first_name}, here's your translation from 🇪🇬 to 🇪🇸:\n\n```\n{translation}```",parse_mode='Markdown')
                            return
                    bot.reply_to(message,  f"{message.from_user.first_name}, here's your translation from {from_lang.upper()} to ES:\n\n```\n{translation}```",parse_mode='Markdown')

                else:
                    print("263")
                    bot_reply_msg = bot.send_message(message.chat.id, f"{message.from_user.first_name}, please reply to this message with the text or voice note you wish to translate to {to_lang.upper()}", reply_markup=telebot.types.ForceReply(selective=True), reply_to_message_id=message.message_id)
                    bot.register_for_reply(bot_reply_msg, handle_trans_reply, to_lang, flag_msg=None, from_lang=None, from_locale=None, to_locale=None)
            except:
                pass
        else:
            print('not text, is voice')
    except:
        pass

# ANY - EN (commands are: en, english, نجليزي|انجليزي) EASIEST IS: en
def check_any_en(message):
    return message.text.split()[0].replace(message.text[0],"").lower() in ("en", "english", "انجليزي", "نجليزي", "ن", "🇬🇧") and not message.text.lower().split()[0][0].isalpha() or message.text.lower().split()[0] == "🇬🇧"
@bot.message_handler(func=check_any_en)
def translate_any_en(message):
    from_lang = None
    to_lang = 'en'
    try:
        text_to_trans = " ".join(message.text.split()[1:])
        translation = gtrans.translate(text=text_to_trans, dest='en').text
        print(message.text.split()[0])
        if message.content_type != "voice" and message.content_type == 'text':
            try:
                if message.text.split()[1]:
                    print('249')
                    from_lang = gtrans.detect(text_to_trans).lang
                    try:
                        if isinstance(from_lang, list) and any(isinstance(item, str) for item in from_lang): # if this is a list and any of the items are str items not chr items
                            from_lang = from_lang[0]
                    except: pass
                    print("from lang at line 179:", from_lang)
                    print(from_lang)
                    match from_lang:
                        case "es":
                            bot.reply_to(message,  f"{message.from_user.first_name}, here's your translation from 🇪🇸 to 🇬🇧:\n\n```\n{translation}```",parse_mode='Markdown')
                            return
                        case "ar":
                            bot.reply_to(message,  f"{message.from_user.first_name}, here's your translation from 🇪🇬 to 🇬🇧:\n\n```\n{translation}```",parse_mode='Markdown')
                            return
                    bot.reply_to(message,  f"{message.from_user.first_name}, here's your translation from {from_lang.upper()} to EN:\n\n```\n{translation}```",parse_mode='Markdown')

                else:
                    print("263")
                    bot_reply_msg = bot.send_message(message.chat.id, f"{message.from_user.first_name}, please reply to this message with the text or voice note you wish to translate to {to_lang.upper()}", reply_markup=telebot.types.ForceReply(selective=True), reply_to_message_id=message.message_id)
                    bot.register_for_reply(bot_reply_msg, handle_trans_reply, to_lang, flag_msg=None, from_lang=None, from_locale=None, to_locale=None)
            except:
                pass
        else:
            print('not text, is voice')
    except:
        pass
# ANY - AR (commands are: *ar, *arabic) EASIEST IS: *ar
def check_any_ar(message):
    return message.text.split()[0].replace(message.text[0],"").lower() in ("ar", "arabic", "🇪🇬") and not message.text.lower().split()[0][0].isalpha() or message.text.lower().split()[0] in ("🇪🇬")
@bot.message_handler(func=check_any_ar)
def translate_any_ar(message):
    from_lang = None
    to_lang = 'ar'
    try:
        text_to_trans = " ".join(message.text.split()[1:])
        translation = gtrans.translate(text=text_to_trans, dest='ar').text
        print(message.text.split()[0])
        if message.content_type != "voice" and message.content_type == 'text':
            try:
                if message.text.split()[1]:
                    print('249')
                    from_lang = gtrans.detect(text_to_trans).lang
                    try:
                        if isinstance(from_lang, list) and any(isinstance(item, str) for item in from_lang): # if this is a list and any of the items are str items not chr items
                            from_lang = from_lang[0]
                    except: pass
                    print("from lang at line 179:", from_lang)
                    print(from_lang)
                    match from_lang:
                        case "en":
                            bot.reply_to(message,  f"{message.from_user.first_name}, here's your translation from 🇬🇧 to 🇪🇬:\n\n```\n{translation}```",parse_mode='Markdown')
                            return
                        case "es":
                            bot.reply_to(message,  f"{message.from_user.first_name}, here's your translation from 🇪🇸 to 🇪🇬:\n\n```\n{translation}```",parse_mode='Markdown')
                            return
                    bot.reply_to(message,  f"{message.from_user.first_name}, here's your translation from {from_lang.upper()} to AR:\n\n```\n{translation}```",parse_mode='Markdown')

                else:
                    print("263")
                    bot_reply_msg = bot.send_message(message.chat.id, f"{message.from_user.first_name}, please reply to this message with the text or voice note you wish to translate to {to_lang.upper()}", reply_markup=telebot.types.ForceReply(selective=True), reply_to_message_id=message.message_id)
                    bot.register_for_reply(bot_reply_msg, handle_trans_reply, to_lang, flag_msg=None, from_lang=None, from_locale=None, to_locale=None)
            except:
                pass
        else:
            print('not text, is voice')
    except:
        pass
# EN - ES (commands are: en-es, *enes, *espanol) EASIEST IS: /enes
def check_en_es(message):
    return message.text.lower().split()[0] in ("en-es", "🇬🇧 🇪🇸", "🇬🇧🇪🇸") or (message.text.split()[0].replace(message.text[0],"").lower() in ("en-es", "enes") and not message.text.lower().split()[0][0].isalpha())
@bot.message_handler(func=check_en_es)
def translate_en_es(message):
    from_lang = 'en'
    to_lang = 'es'
    try:
        text_to_trans = " ".join(message.text.split()[1:])
        translation = gtrans.translate(text=text_to_trans, src=from_lang,dest=to_lang).text
        print(message.text.split()[0])
        if message.content_type != "voice" and message.content_type == 'text':
            try:
                if message.text.split()[1]:
                    print('249')
                    from_lang = gtrans.detect(text_to_trans).lang
                    try:
                        if isinstance(from_lang, list) and any(isinstance(item, str) for item in from_lang): # if this is a list and any of the items are str items not chr items
                            from_lang = from_lang[0]
                    except: pass
                    print("from lang at line 179:", from_lang)
                    print(from_lang)
                    bot.reply_to(message,  f"{message.from_user.first_name}, here's your translation from {from_lang.upper()} to ES:\n\n```\n{translation}```",parse_mode='Markdown')

                else:
                    print("263")
                    bot_reply_msg = bot.send_message(message.chat.id, f"{message.from_user.first_name}, please reply to this message with the text or voice note you wish to translate to {to_lang.upper()}", reply_markup=telebot.types.ForceReply(selective=True), reply_to_message_id=message.message_id)
                    bot.register_for_reply(bot_reply_msg, handle_trans_reply, to_lang, flag_msg=None, from_lang=None, from_locale=None, to_locale=None)
            except:
                pass
        else:
            print('not text, is voice')
    except:
        pass
# ES - EN (commands are: es-en, *esen, *ingles) EASIEST IS: ingles
def check_es_en(message):
    return message.text.lower().split()[0] in ("es-en", "🇪🇸 🇬🇧", "🇪🇸🇬🇧") or (message.text.split()[0].replace(message.text[0],"").lower() in ("es-en", "esen", "ingles") and not message.text.lower().split()[0][0].isalpha())
@bot.message_handler(func=check_es_en)
def translate_es_en(message):
    from_lang = 'es'
    to_lang = 'en'
    try:
        text_to_trans = " ".join(message.text.split()[1:])
        translation = gtrans.translate(text=text_to_trans, src=from_lang,dest=to_lang).text
        print(message.text.split()[0])
        if message.content_type != "voice" and message.content_type == 'text':
            try:
                if message.text.split()[1]:
                    print('249')
                    from_lang = gtrans.detect(text_to_trans).lang
                    try:
                        if isinstance(from_lang, list) and any(isinstance(item, str) for item in from_lang): # if this is a list and any of the items are str items not chr items
                            from_lang = from_lang[0]
                    except: pass
                    print("from lang at line 179:", from_lang)
                    print(from_lang)
                    bot.reply_to(message,  f"{message.from_user.first_name}, here's your translation from {from_lang.upper()} to EN:\n\n```\n{translation}```",parse_mode='Markdown')

                else:
                    print("263")
                    bot_reply_msg = bot.send_message(message.chat.id, f"{message.from_user.first_name}, please reply to this message with the text or voice note you wish to translate to {to_lang.upper()}", reply_markup=telebot.types.ForceReply(selective=True), reply_to_message_id=message.message_id)
                    bot.register_for_reply(bot_reply_msg, handle_trans_reply, to_lang, flag_msg=None, from_lang=None, from_locale=None, to_locale=None)
            except:
                pass
        else:
            print('not text, is voice')
    except:
        pass
# ES - AR (commands are: es-ar, *arabica/arábica, *esar) EASIEST IS: arabica
def check_es_ar(message):
    return message.text.lower().split()[0] in ("es-ar", "🇪🇸 🇪🇬", "🇪🇸🇪🇬") or (message.text.split()[0].replace(message.text[0],"").lower() in ("esar", "arabica", "arábica") and not message.text.lower().split()[0][0].isalpha())
@bot.message_handler(func=check_es_ar)
def translate_es_ar(message):
    from_lang = 'es'
    to_lang = 'ar'
    try:
        text_to_trans = " ".join(message.text.split()[1:])
        translation = gtrans.translate(text=text_to_trans, src=from_lang,dest=to_lang).text
        print(message.text.split()[0])
        if message.content_type != "voice" and message.content_type == 'text':
            try:
                if message.text.split()[1]:
                    print('249')
                    from_lang = gtrans.detect(text_to_trans).lang
                    try:
                        if isinstance(from_lang, list) and any(isinstance(item, str) for item in from_lang): # if this is a list and any of the items are str items not chr items
                            from_lang = from_lang[0]
                    except: pass
                    print("from lang at line 179:", from_lang)
                    print(from_lang)
                    bot.reply_to(message,  f"{message.from_user.first_name}, here's your translation from {from_lang.upper()} to AR:\n\n```\n{translation}```",parse_mode='Markdown')

                else:
                    print("263")
                    bot_reply_msg = bot.send_message(message.chat.id, f"{message.from_user.first_name}, please reply to this message with the text or voice note you wish to translate to {to_lang.upper()}", reply_markup=telebot.types.ForceReply(selective=True), reply_to_message_id=message.message_id)
                    bot.register_for_reply(bot_reply_msg, handle_trans_reply, to_lang, flag_msg=None, from_lang=None, from_locale=None, to_locale=None)
            except:
                pass
        else:
            print('not text, is voice')
    except:
        pass
# AR - ES (commands are: ar-es, *ares, سباني, اسباني, س) EASIEST IS: !س or !سباني
def check_ar_es(message):
    return message.text.lower().split()[0] in ("ar-es", "🇪🇬 🇪🇸", "🇪🇬🇪🇸") or (message.text.split()[0].replace(message.text[0],"").lower() in ("ares", "سباني", "اسباني", "س") and not message.text.lower().split()[0][0].isalpha())
@bot.message_handler(func=check_ar_es)
def translate_ar_es(message):
    from_lang = 'ar'
    to_lang = 'es'
    try:
        text_to_trans = " ".join(message.text.split()[1:])
        translation = gtrans.translate(text=text_to_trans, src='ar',dest='es').text
        print(message.text.split()[0])
        if message.content_type != "voice" and message.content_type == 'text':
            try:
                if message.text.split()[1]:
                    print('249')
                    from_lang = gtrans.detect(text_to_trans).lang
                    try:
                        if isinstance(from_lang, list) and any(isinstance(item, str) for item in from_lang): # if this is a list and any of the items are str items not chr items
                            from_lang = from_lang[0]
                    except: pass
                    print("from lang at line 179:", from_lang)
                    print(from_lang)
                    bot.reply_to(message,  f"{message.from_user.first_name}, here's your translation from {from_lang.upper()} to ES:\n\n```\n{translation}```",parse_mode='Markdown')

                else:
                    print("263")
                    bot_reply_msg = bot.send_message(message.chat.id, f"{message.from_user.first_name}, please reply to this message with the text or voice note you wish to translate to {to_lang.upper()}", reply_markup=telebot.types.ForceReply(selective=True), reply_to_message_id=message.message_id)
                    bot.register_for_reply(bot_reply_msg, handle_trans_reply, to_lang, flag_msg=None, from_lang=None, from_locale=None, to_locale=None)
            except:
                pass
        else:
            print('not text, is voice')
    except:
        pass
# AR - EN (commands are: ar-en, *aren, نجليزي, انجليزي, ن) EASIEST IS: !نجليزي
def check_ar_en(message):
    return message.text.lower().split()[0] in ("ar-en", "🇪🇬 🇬🇧", "🇪🇬🇬🇧") or (message.text.split()[0].replace(message.text[0],"").lower() in ("aren", "ن", "انجليزي", "نجليزي") and not message.text.lower().split()[0][0].isalpha())
@bot.message_handler(func=check_ar_en)
def translate_ar_en(message):
    from_lang = 'ar'
    to_lang = 'en'
    try:
        text_to_trans = " ".join(message.text.split()[1:])
        translation = gtrans.translate(text=text_to_trans, src=from_lang,dest=to_lang).text
        print(message.text.split()[0])
        if message.content_type != "voice" and message.content_type == 'text':
            try:
                if message.text.split()[1]:
                    print('249')
                    from_lang = gtrans.detect(text_to_trans).lang
                    try:
                        if isinstance(from_lang, list) and any(isinstance(item, str) for item in from_lang): # if this is a list and any of the items are str items not chr items
                            from_lang = from_lang[0]
                    except: pass
                    print("from lang at line 179:", from_lang)
                    print(from_lang)
                    bot.reply_to(message,  f"{message.from_user.first_name}, here's your translation from {from_lang.upper()} to EN:\n\n```\n{translation}```",parse_mode='Markdown')

                else:
                    print("263")
                    bot_reply_msg = bot.send_message(message.chat.id, f"{message.from_user.first_name}, please reply to this message with the text or voice note you wish to translate to {to_lang.upper()}", reply_markup=telebot.types.ForceReply(selective=True), reply_to_message_id=message.message_id)
                    bot.register_for_reply(bot_reply_msg, handle_trans_reply, to_lang, flag_msg=None, from_lang=None, from_locale=None, to_locale=None)
            except:
                pass
        else:
            print('not text, is voice')
    except:
        pass
# EN - AR (commands are: en-ar, *enar) EASIEST IS: *enar
def check_en_ar(message):
    return (message.text.lower().split()[0] in ("en-ar", "🇬🇧 🇪🇬", "🇬🇧🇪🇬") ) or ( message.text.split()[0].replace(message.text[0],"").lower() == "enar" and not message.text.lower().split()[0][0].isalpha() )
@bot.message_handler(func=check_en_ar)
def translate_en_ar(message):
    from_lang = 'en'
    to_lang = 'ar'
    try:
        text_to_trans = " ".join(message.text.split()[1:])
        translation = gtrans.translate(text=text_to_trans, src=from_lang,dest=to_lang).text
        print(message.text.split()[0])
        if message.content_type != "voice" and message.content_type == 'text':
            try:
                if message.text.split()[1]:
                    print('249')
                    from_lang = gtrans.detect(text_to_trans).lang
                    try:
                        if isinstance(from_lang, list) and any(isinstance(item, str) for item in from_lang): # if this is a list and any of the items are str items not chr items
                            from_lang = from_lang[0]
                    except: pass
                    print("from lang at line 179:", from_lang)
                    print(from_lang)
                    bot.reply_to(message,  f"{message.from_user.first_name}, here's your translation from {from_lang.upper()} to AR:\n\n```\n{translation}```",parse_mode='Markdown')

                else:
                    print("263")
                    bot_reply_msg = bot.send_message(message.chat.id, f"{message.from_user.first_name}, please reply to this message with the text or voice note you wish to translate to {to_lang.upper()}", reply_markup=telebot.types.ForceReply(selective=True), reply_to_message_id=message.message_id)
                    bot.register_for_reply(bot_reply_msg, handle_trans_reply, to_lang, flag_msg=None, from_lang=None, from_locale=None, to_locale=None)
            except:
                pass
        else:
            print('not text, is voice')
    except:
        pass

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

@bot.callback_query_handler(lambda call: call.message.reply_to_message.content_type != "voice")
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
        bot.reply_to(call.message.reply_to_message, f"{call.message.reply_to_message.from_user.first_name}, here's your translation from {from_lang.upper()} to {to_lang.upper()}:\n\n```\n{translation}```",parse_mode='Markdown')
        bot.delete_message(call.message.chat.id, call.message.id)
    else:
        print("482")
        bot_reply_msg = bot.send_message(call.message.chat.id, f"{call.message.reply_to_message.from_user.first_name}, please reply to this message with the text or voice note you wish to translate to {to_lang.upper()}", reply_markup=telebot.types.ForceReply(selective=True), reply_to_message_id=call.message.reply_to_message.message_id)
        #bot_reply_msg = bot.reply_to(call.message.reply_to_message, f"{call.message.reply_to_message.from_user.first_name}, Reply to this message with the text you wish to translate to {to_lang.upper()}")
        bot.delete_message(call.message.chat.id, call.message.id)
        bot.delete_message(call.message.reply_to_message.chat.id, call.message.reply_to_message.message_id)
        bot.register_for_reply(bot_reply_msg, handle_trans_reply, to_lang, flag_msg=None, from_lang=None, from_locale=None, to_locale=None)

def handle_trans_reply(message, to_lang, flag_msg, from_lang, from_locale, to_locale):
    print("entered handle trans reply")
    print("to_lang at line 450:", to_lang)
    if message.reply_to_message != None:
        if message.content_type == "text":
            text_to_trans = message.text
            if from_lang is None:
                from_lang = gtrans.detect(text_to_trans).lang
                if isinstance(from_lang, list) and any(isinstance(item, str) for item in from_lang): # if this is a list and any of the items are str items not chr items
                    from_lang = from_lang[0]
                print("from lang at line 423:", from_lang)
            translation = gtrans.translate(text=text_to_trans, dest=to_lang, src=from_lang).text
            bot.reply_to(message, f"{message.from_user.first_name}, here's your translation from {from_lang.upper()} to {to_lang.upper()}:\n\n```\n{translation}```",parse_mode='Markdown')
            bot.delete_message(message.chat.id, message.reply_to_message.message_id)

        elif message.content_type == "voice": # reply to bot with voice note to translate
            print("reply to bot with voice note to translate")
            translate_voice(message, from_lang, to_lang, from_locale, to_locale)
        if flag_msg:
            if flag_msg.reply_to_message: # choose a language text
                bot.delete_message(message.chat.id, flag_msg.reply_to_message.message_id)
            bot.delete_message(message.chat.id, flag_msg.message_id)

'''
steps for voice translation:
1.send /v
2.choose from_region
3.reply with the voice note
4.you get a reply with transcription and translation
'''

@bot.message_handler(commands=["v","ص","voice","صوت"])
def init_voice_trans(message):
    bot_reply_choose_lang(message)

#@bot.message_handler(content_types=["voice"])
def translate_voice(message:telebot.types.Message, from_lang, to_lang, from_locale, to_locale):
    RECOGNIZED_LANG=None
    global global_from_lang
    global global_to_lang
    print("TRANSLATE VOICE", from_locale, to_locale)
    print("THIS", message.content_type, message.voice.duration)
    chat_id = message.chat.id

    # Get the voice note file
    file_path = bot.get_file(message.voice.file_id).file_path
    print(file_path)
    voice_data = bot.download_file(file_path)

    # Save the voice note locally
    voice_file_path = "voice_note.ogg"
    with open(voice_file_path, 'wb') as voice_file:
        voice_file.write(voice_data)

    # Convert the voice note to a format recognized by the speech recognition library
    audio = AudioSegment.from_file(voice_file_path, format="ogg")
    audio.export("voice_note.wav", format="wav")

    recognizer = sr.Recognizer()
    with sr.AudioFile("voice_note.wav") as source:
        transcription=None
        audio_data = recognizer.record(source)
        speech_config = speechsdk.SpeechConfig(subscription='a72af3632e1e4ae3826210e3c76b56d9', region="westeurope")
        audio_config = speechsdk.audio.AudioConfig(filename='voice_note.wav')
        lang_configs= [speechsdk.languageconfig.SourceLanguageConfig("en-US"), speechsdk.languageconfig.SourceLanguageConfig("ar-EG")
        ]
        auto_detect_source_language_config = speechsdk.languageconfig.AutoDetectSourceLanguageConfig(sourceLanguageConfigs=lang_configs)
        if from_lang is None:
            print("NO FROM LANG PROVIDED, USING THE AUTO CONFIG")
            speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config,auto_detect_source_language_config=auto_detect_source_language_config,audio_config=audio_config)
        else:
            print("FROM LANG PROVIDED, USING THAT LOCALE")
            speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config,language=from_locale,audio_config=audio_config)
        result = speech_recognizer.recognize_once()
        
        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            auto_detect_source_language_result = speechsdk.AutoDetectSourceLanguageResult(result)
            transcription = result.text
            RECOGNIZED_LANG = auto_detect_source_language_result.language
            print("Recognized: {} in language {}".format(result.text, auto_detect_source_language_result.language))

        # match picked_region:
        #     case "euwest":
        #         #transcription = recognizer.recognize_azure(audio_data, key='a72af3632e1e4ae3826210e3c76b56d9', location='westeurope')[0]
        #         speech_config = speechsdk.SpeechConfig(subscription='a72af3632e1e4ae3826210e3c76b56d9', region="westeurope")
        #         audio_config = speechsdk.audio.AudioConfig(filename='voice_note.wav')
        #         lang_configs= [speechsdk.languageconfig.SourceLanguageConfig("en-US"),
        #         speechsdk.languageconfig.SourceLanguageConfig("es-ES"), speechsdk.languageconfig.SourceLanguageConfig("ar-EG")
        #         ]
        #         auto_detect_source_language_config = speechsdk.languageconfig.AutoDetectSourceLanguageConfig(sourceLanguageConfigs=lang_configs)
        #         speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config,auto_detect_source_language_config=auto_detect_source_language_config,audio_config=audio_config)
        #         result = speech_recognizer.recognize_once()
        #         if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        #             auto_detect_source_language_result = speechsdk.AutoDetectSourceLanguageResult(result)
        #             transcription = result.text
        #             print("Recognized: {} in language {}".format(result.text, auto_detect_source_language_result.language))
        #     case "uaenorth":
        #         transcription = recognizer.recognize_azure(audio_data, key='b1846da7cbb6402cae4c02b87d636d38', location='uaenorth',  language='ar-EG')[0]
        #     case "qatar":
        #         transcription = recognizer.recognize_azure(audio_data, key='ce5838858ee74d06bb954d8af2da9d1c', location='qatarcentral', language='ar-QA')[0]
        #         print("transcribing with the qatar region")
        #     case None:
        #         translate_voice(message,from_lang,to_lang)
        #         return

        if transcription is None:
            bot.reply_to(message, "Couldn't detect speech! Please try again.")
            return
        
        print(to_lang)
        print(from_lang)
        if from_lang is None:
            try:
                print("detecting from_lang from transcription")
                from_lang = gtrans.detect(transcription).lang
            except:
                bot.reply_to(message, "`Couldn't detect language! Please try again.`")
                return
        print(from_lang)
        translation = gtrans.translate(transcription, src=from_lang, dest=to_lang)
        print(transcription,translation.text)
        print(from_locale, to_locale)
        print(RECOGNIZED_LANG)
        if from_locale != 'en':
            bot.reply_to(message, f"\n`Translated from {from_locale}:````\n{transcription}```\n`into {to_locale}:`\n```\n{translation.text}```\n",parse_mode="Markdown")
        else:
            bot.reply_to(message, f"\n`Translated from {RECOGNIZED_LANG}:````\n{transcription}```\n`into {to_locale}:`\n```\n{translation.text}```\n",parse_mode="Markdown")
        # feed to_lang into this function


def choose_region_reply(message, from_lang, to_lang):
    print("to_lang at line 529:", to_lang)
    global global_from_lang ,global_to_lang
    global_from_lang = from_lang
    global_to_lang = to_lang

    region_markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    btns = {
        "euwest_btn" : telebot.types.InlineKeyboardButton("EU West", callback_data="cb_euwest"),
        "uae_btn" : telebot.types.InlineKeyboardButton("UAE North", callback_data="cb_uae"),
        "qatar_btn" : telebot.types.InlineKeyboardButton("Qatar Central", callback_data="cb_qatar")
    }

    for e in btns:
        region_markup.add(btns[e])
    bot.reply_to(message, "Choose a speech region from below:", reply_markup=region_markup)

@bot.callback_query_handler(lambda call: True)
def region_callback(call):
    match call.data:
        case "cb_euwest":
            print("picked eu west")
            picked_region = "euwest"
        case "cb_uae":
            print("picked uae")
            picked_region = "uaenorth"
        case "cb_qatar":
            print("picked qatar")
            picked_region = "qatar"
    
    print(picked_region)
    print(global_from_lang, global_to_lang)
    translate_voice(call.message.reply_to_message, global_from_lang, global_to_lang, picked_region)
    bot.delete_message(call.message.chat.id, call.message.message_id)

bot.polling()

# TO ADD/FIX:
# upon sending a voice note reply with a choose_voice_note_region option

# make sure to delete the temporary file or use the file that telegram provides