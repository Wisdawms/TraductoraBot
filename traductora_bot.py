import os
import subprocess
from dotenv import load_dotenv
load_dotenv()
import telebot
import requests
from googletrans import Translator
import re
from pydub import AudioSegment, silence
import azure.cognitiveservices.speech as speechsdk
from babel import Locale
from keep_alive import *
import datetime

BOT_API = os.getenv("API_KEY2")
bot = telebot.TeleBot(str(BOT_API))
gtrans = Translator()
translation = gtrans.translate(dest='es', text=None)
REGION_KEY = os.getenv('REGION_KEY')
REGION_NAME = os.getenv('REGION_NAME')

@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(message.chat.id,"You can use the country-flag emojis to translate stuff!\n\nExamples:\n🇬🇧 [text] -> This will translate any input text to English\n\n🇬🇧 🇪🇸 [text] -> This will translate from English to Spanish\n\nOr you can just send a flag emoji then reply with the text that you want to translate.\n\nYou can also reply to a message with a country-flag emoji to instantly translate it to that language! _Try it out by replying to this message with the Spain country-flag emoji_ 🇪🇸.\n\n`You can still use the two-emoji format when replying to force the source language instead of having the translation API detect it.`\n⚠️ Please don't send in any sensitive data or information through either the text messages or voice-notes, as in order for the bot to work, it has to read this data. ⚠️",parse_mode="Markdown")

@bot.message_handler(commands=["help"])
def help(message):
    bot.send_message(message.chat.id, bot.get_my_description().description)

global_t_msg = None
choose_language_txt : str = "Choose a language, or reply with a country-flag emoji to set the output language:"
please_reply_txt : str = "reply to this message with the text"

def delete_sound_files(ogg_file,wav_file):
    try:
        os.remove(ogg_file)
        os.remove(wav_file)
    except: pass

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

def normalize_country_code(code:str):
    if code:
        try:
            return ''.join(chr(ord(char) - ord('🇦') + ord('A')) for char in code)
        except:
            print("COULDN'T NORMALIZE CODE")
            pass
    return None

def extract_language_codes(input_string):
    print("EXTRACTING LANG CODES")
    hit = False
    first_word = input_string.split()[0]
    if len(first_word) < 2:
        hit = False
        return None, None, hit, None, None
    try:
        if get_language_code(normalize_country_code(first_word[0]+first_word[1])):
            if len(first_word) <= 2:
                to_lang_code = first_word[0]+first_word[1]
                to_lang_code_normalized = normalize_country_code(to_lang_code)
                to_lang = get_language_code(normalize_country_code(to_lang_code))
                hit = True
                print("from_lang_normalized is:", to_lang_code_normalized)
                return None, to_lang, hit, None, to_lang_code_normalized

            elif len(first_word) <= 4:
                from_lang_code = first_word[0]+first_word[1]
                from_lang_code_normalized = normalize_country_code(from_lang_code)
                from_lang =  get_language_code(normalize_country_code(from_lang_code))
                print("from lang at line 56:", from_lang)
                to_lang_code = first_word[2]+first_word[3]
                to_lang_code_normalized = normalize_country_code(to_lang_code)
                to_lang = get_language_code(normalize_country_code(to_lang_code))
                hit = True
                print("from_lang_normalized is:", from_lang_code_normalized)
                print("to_lang_normalized is:", to_lang_code_normalized)
                return from_lang, to_lang, hit, from_lang_code_normalized, to_lang_code_normalized
        else:
            hit = False
            return None, None, hit, None, None
    except:
        print('ERROR GETTING LANGUAGE CODE')
        pass


def contains_country_flag_emoji(text):
    # Define a regular expression pattern for country flag emojis
    country_flag_pattern = re.compile(r'[\U0001F1E6-\U0001F1FF]{2}')
    return bool(country_flag_pattern.search(text))

def check_flags(message):
    print('started checking for flags')
    to_lang = None
    from_lang = None
    if check_any_en(message) is True:
        to_lang='en'
    elif check_any_es(message) is True:
        to_lang='es'
    elif check_any_ar(message) is True:
        to_lang='ar'

    elif check_ar_es(message) is True:
        to_lang='es'
        from_lang='ar'
    elif check_ar_en(message) is True:
        to_lang='en'
        from_lang='ar'
    elif check_es_en(message) is True:
        to_lang='en'
        from_lang = 'es'
    elif check_es_ar(message) is True:
        to_lang='ar'
        from_lang='es'
    elif check_en_ar(message) is True:
        to_lang='ar'
        from_lang='en'
    elif check_en_es(message) is True:
        to_lang='es'
        from_lang='en'

    msg_parts = message.text.split(None, 1) if message.text else message.split(None, 1)
    from_locale=None
    to_locale = None
    print("from lang at line 145:", from_lang)
    txt_to_trans = msg_parts[1] if len(msg_parts) > 1 else None
    lang_codes_result = extract_language_codes(msg_parts[0])
    print("language code extraction result:",lang_codes_result)
    try:
        from_locale = get_locale_from_country_code(lang_codes_result[3])
        print("at line 151, from_locale is: ", from_locale)
    except:
        print('ERROR GETTING FROM_LOCALE')
        pass

    try:
        to_locale = get_locale_from_country_code(lang_codes_result[4])
        print("at line 158, to_locale is: ", to_locale)
    except:
        print('ERROR GETTING TO_LOCALE')
        pass

    if lang_codes_result:
        if message.reply_to_message and message.reply_to_message.content_type == "voice":
            print("reply to message is a voice note")
            if lang_codes_result[0] is not None:
                from_lang = lang_codes_result[0]
            if lang_codes_result[1] is not None:
                to_lang = lang_codes_result[1]
            try:
                trans_voice_results = translate_voice_message(message.reply_to_message, from_lang, to_lang, from_locale, to_locale)
                ogg_file, wav_file = trans_voice_results[0], trans_voice_results[1]
            finally:
                delete_sound_files(ogg_file, wav_file)
            
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
        if lang_codes_result[1] is not None:
            to_lang = lang_codes_result[1]
            print("from lang at line 190:", from_lang)
        else:
            if message.reply_to_message is not None:
                if txt_to_trans and (message.reply_to_message.text not in choose_language_txt or message.reply_to_message.text in please_reply_txt):
                    from_lang = gtrans.detect(txt_to_trans).lang
                    if isinstance(from_lang, list) and any(isinstance(item, str) for item in from_lang): # if this is a list and any of the items are str items not chr items
                        from_lang = from_lang[0]
                    print("from lang at line 197:", from_lang)
            else:
                from_lang = None
                print("from lang at line 200:", from_lang)
        to_lang = lang_codes_result[1]
        return True, from_lang, to_lang, txt_to_trans, from_locale, to_locale
    elif lang_codes_result is None:
        print('No language codes result found')
        return False

@bot.message_handler(func=check_flags)
def translate_two_flags(message):
    global global_t_msg
    print('again t_msg is:', global_t_msg)
    if message.content_type == 'voice':
        print("reply_message is a voice")
        try:
            trans_voice_results = translate_voice_message(message.reply_to_message, from_lang, to_lang, from_locale, to_locale)
            ogg_file, wav_file = trans_voice_results[0], trans_voice_results[1]
        finally:
            delete_sound_files(ogg_file, wav_file)
            
        return
    if message.reply_to_message is not None:
        if extract_language_codes(message.text)[2] is False and (message.reply_to_message.text == choose_language_txt):
            bot.reply_to(message, "Language code not found. Sorry!")
            return
        elif message.reply_to_message.content_type == "voice":
            print("reply_message is a voice")
            try:
                trans_voice_results = translate_voice_message(message.reply_to_message, from_lang, to_lang, from_locale, to_locale)
                ogg_file, wav_file = trans_voice_results[0], trans_voice_results[1]
            finally:
                delete_sound_files(ogg_file, wav_file)
            
            return
    try:
        check_result = check_flags(message)
        print("got check results")
        if check_result[0]:
            print("check results index 0 is true")
            from_lang, to_lang, text_to_trans, from_locale, to_locale = check_result[1], check_result[2], check_result[3], check_result[4], check_result[5]
            print("got from, to, and txt_to_trans, from_locale, to_locale", from_lang, to_lang, text_to_trans, from_locale, to_locale)
            if text_to_trans is None:
                print('txt_to_trans is None')
                if message.reply_to_message is not None:
                    if message.reply_to_message.text == choose_language_txt:
                        text_to_trans = global_t_msg.text.split('\n')
                        text_to_trans[0] = ' '.join(text_to_trans[0].split()[1:])
                        text_to_trans='\n'.join(text_to_trans)
                        print(' I think I got it its', text_to_trans )
            print("TXT TO TRANS???", check_result[3])
            print(from_locale, to_locale)

            try:
                if message.reply_to_message is not None and (message.reply_to_message.text not in choose_language_txt or message.reply_to_message.text in please_reply_txt):
                    print("this is a reply, translating text")
                    print(message.reply_to_message.text)
                    if from_lang is None:
                        print('detecting from lang from reply text')
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
                            from_lang = gtrans.detect(text_to_trans).lang
                            if isinstance(from_lang, list) and any(isinstance(item, str) for item in from_lang): # if this is a list and any of the items are str items not chr items
                                from_lang = from_lang[0]
                            print("from lang at line 153:", from_lang)
                        print("from lang at line 160:", from_lang)
                        print('txt to trans at 258 is', text_to_trans)
                        print('translating from:', from_lang, 'to:', to_lang)
                        translation = gtrans.translate(text=text_to_trans, dest=to_lang, src=from_lang).text
                        print('found translation, it is:', translation)
                        if message.reply_to_message:
                            if message.reply_to_message.text == choose_language_txt:
                                print('DANGEROUS CHECK IF DELETING ANYTHING IMPORTANT')
                                bot.reply_to(global_t_msg, f"{message.from_user.first_name}, here's your translation from {from_lang.upper()} to {to_lang.upper()}:\n\n```\n{translation}```",parse_mode='Markdown')
                                if message.reply_to_message:
                                    bot.delete_message(message.reply_to_message.chat.id, message.reply_to_message.message_id)
                                bot.delete_message(message.chat.id, message.message_id)
                                return
                        print('268')
                        bot.reply_to(message, f"{message.from_user.first_name}, here's your translation from {from_lang.upper()} to {to_lang.upper()}:\n\n```\n{translation}```",parse_mode='Markdown')
                    else:
                        print("223")
                        #bot_reply_msg = bot.send_message(message.chat.id, f"{message.from_user.first_name}, please reply to this message with the text or voice note you wish to translate to {to_lang.upper()}", reply_markup=telebot.types.ForceReply(selective=True), reply_to_message_id=message.message_id)
                        bot_reply_msg = bot.reply_to(message, f"{message.from_user.first_name}, please reply to this message with the text or voice note you wish to translate to {to_lang.upper()}", reply_markup=telebot.types.ForceReply(selective=True))
                        print('found bot_reply_msg')
                        try:
                            flag_msg = message
                        except: pass
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

def check_any_en(message):
    return message.text.split()[0].replace(message.text[0],"").lower() in ("en", "english", "انجليزي", "نجليزي", "ن", "🇬🇧") and not message.text.lower().split()[0][0].isalpha() or message.text.lower().split()[0] == "🇬🇧"
@bot.message_handler(func=check_any_en)
def translate_any_en(message):
    from_lang = None
    to_lang = 'en'
    print('ENTERED', from_lang, to_lang)
    if message.reply_to_message is None and not len(message.text.split()) > 1:
        print("line 310 any en")
        bot_reply_msg = bot.send_message(message.chat.id, f"{message.from_user.first_name}, please reply to this message with the text or voice note you wish to translate to English", reply_markup=telebot.types.ForceReply(selective=True), reply_to_message_id=message.message_id)
        bot.register_for_reply(bot_reply_msg, handle_trans_reply, to_lang, flag_msg=message, from_lang=from_lang, from_locale=None, to_locale=None)
        return
    try:
        if message.reply_to_message is not None: # if this has a reply
            if message.reply_to_message.content_type == 'text': # to text 
                text_to_trans = message.reply_to_message.text
                print('333')
                translation = gtrans.translate(text=text_to_trans,dest=to_lang).text
                print('249')
                if from_lang is None:
                    from_lang = gtrans.detect(text_to_trans).lang
                try:
                    if isinstance(from_lang, list) and any(isinstance(item, str) for item in from_lang): # if this is a list and any of the items are str items not chr items
                        from_lang = from_lang[0]
                except: pass
                print("from lang at line 327:", from_lang)
                if from_lang is not None:
                    match from_lang:
                        case "es":
                            bot.reply_to(message.reply_to_message,  f"{message.from_user.first_name}, here's your translation from 🇪🇸 to 🇬🇧:\n\n```\n{translation}```",parse_mode='Markdown')
                            return
                        case "ar":
                            bot.reply_to(message.reply_to_message,  f"{message.from_user.first_name}, here's your translation from 🇪🇬 to 🇬🇧:\n\n```\n{translation}```",parse_mode='Markdown')
                            return
                bot.reply_to(message.reply_to_message,  f"{message.from_user.first_name}, here's your translation from {from_lang.upper()} to EN:\n\n```\n{translation}```",parse_mode='Markdown')
                return

        elif message.reply_to_message is None:
            print('checking if message doesnt have reply')
            if len(message.text.split()) > 1:
                text_to_trans = message.text.split('\n')
                text_to_trans[0] = ' '.join(text_to_trans[0].split()[1:])
                text_to_trans='\n'.join(text_to_trans)
                translation = gtrans.translate(text_to_trans, dest=to_lang).text
                if from_lang is None:
                    from_lang = gtrans.detect(text_to_trans).lang
                try:
                    if isinstance(from_lang, list) and any(isinstance(item, str) for item in from_lang): # if this is a list and any of the items are str items not chr items
                        from_lang = from_lang[0]
                except: pass
                bot.reply_to(message,  f"{message.from_user.first_name}, here's your translation from {from_lang.upper()} to EN:\n\n```\n{translation}```",parse_mode='Markdown')
    except:
        pass

def check_any_es(message):
    return message.text.split()[0].replace(message.text[0],"").lower() in ("espanol", "español", "spanish", "es", "سباني", "اسباني") and not message.text.lower().split()[0][0].isalpha() or message.text.lower().split()[0] == "🇪🇸"
@bot.message_handler(func=check_any_es)
def translate_any_es(message):
    from_lang = None
    to_lang = 'es'
    print('ENTERED', from_lang, to_lang)
    if message.reply_to_message is None and not len(message.text.split()) > 1:
        print("line 365 any es")
        bot_reply_msg = bot.send_message(message.chat.id, f"{message.from_user.first_name}, please reply to this message with the text or voice note you wish to translate to Spanish", reply_markup=telebot.types.ForceReply(selective=True), reply_to_message_id=message.message_id)
        bot.register_for_reply(bot_reply_msg, handle_trans_reply, to_lang, flag_msg=message, from_lang=from_lang, from_locale=None, to_locale=None)
        return
    try:
        if message.reply_to_message is not None: # if this has a reply
            if message.reply_to_message.content_type == 'text': # to text 
            # (was indented) if len(message.reply_to_message.text.split()) > 1 or len(message.reply_to_message.text.split('')) > 1: # if message has more than one character or more than one word
                text_to_trans = message.reply_to_message.text
                translation = gtrans.translate(text=text_to_trans,dest=to_lang).text
                if from_lang is None:
                    from_lang = gtrans.detect(text_to_trans).lang
                try:
                    if isinstance(from_lang, list) and any(isinstance(item, str) for item in from_lang): # if this is a list and any of the items are str items not chr items
                        from_lang = from_lang[0]
                except: pass
                print("from lang at line 179:", from_lang)
                if from_lang is not None:
                    match from_lang:
                        case "en":
                            bot.reply_to(message.reply_to_message,  f"{message.from_user.first_name}, here's your translation from 🇬🇧 to 🇪🇸:\n\n```\n{translation}```",parse_mode='Markdown')
                            return
                        case "ar":
                            bot.reply_to(message.reply_to_message,  f"{message.from_user.first_name}, here's your translation from 🇪🇬 to 🇪🇸:\n\n```\n{translation}```",parse_mode='Markdown')
                            return
                bot.reply_to(message.reply_to_message,  f"{message.from_user.first_name}, here's your translation from {from_lang.upper()} to ES:\n\n```\n{translation}```",parse_mode='Markdown')
                return
        elif message.reply_to_message is None:
            print('checking if message doesnt have reply')
            if len(message.text.split()) > 1:
                text_to_trans = message.text.split('\n')
                text_to_trans[0] = ' '.join(text_to_trans[0].split()[1:])
                text_to_trans='\n'.join(text_to_trans)
                translation = gtrans.translate(text_to_trans, dest=to_lang).text
                if from_lang is None:
                    from_lang = gtrans.detect(text_to_trans).lang
                try:
                    if isinstance(from_lang, list) and any(isinstance(item, str) for item in from_lang): # if this is a list and any of the items are str items not chr items
                        from_lang = from_lang[0]
                except: pass
                bot.reply_to(message,  f"{message.from_user.first_name}, here's your translation from {from_lang.upper()} to ES:\n\n```\n{translation}```",parse_mode='Markdown')
    except:
        pass

def check_any_ar(message):
    return message.text.split()[0].replace(message.text[0],"").lower() in ("ar", "arabic", "🇪🇬") and not message.text.lower().split()[0][0].isalpha() or message.text.lower().split()[0] in ("🇪🇬")
@bot.message_handler(func=check_any_ar)
def translate_any_ar(message):
    from_lang = None
    to_lang = 'ar'
    print('ENTERED', from_lang, to_lang)
    if message.reply_to_message is None and not len(message.text.split()) > 1:
        print("line 416 any ar")
        bot_reply_msg = bot.send_message(message.chat.id, f"{message.from_user.first_name}, please reply to this message with the text or voice note you wish to translate to Arabic", reply_markup=telebot.types.ForceReply(selective=True), reply_to_message_id=message.message_id)
        bot.register_for_reply(bot_reply_msg, handle_trans_reply, to_lang, flag_msg=message, from_lang=from_lang, from_locale=None, to_locale=None)
        return
    try:
        if message.reply_to_message is not None: # if this has a reply
            if message.reply_to_message.content_type == 'text': # to text 
                text_to_trans = message.reply_to_message.text
                translation = gtrans.translate(text=text_to_trans,dest=to_lang).text
                if from_lang is None:
                    from_lang = gtrans.detect(text_to_trans).lang
                try:
                    if isinstance(from_lang, list) and any(isinstance(item, str) for item in from_lang): # if this is a list and any of the items are str items not chr items
                        from_lang = from_lang[0]
                except: pass
                print("from lang at line 431:", from_lang)
                if from_lang is not None:
                    match from_lang:
                        case "en":
                            bot.reply_to(message.reply_to_message,  f"{message.from_user.first_name}, here's your translation from 🇬🇧 to 🇪🇬:\n\n```\n{translation}```",parse_mode='Markdown')
                            return
                        case "es":
                            bot.reply_to(message.reply_to_message,  f"{message.from_user.first_name}, here's your translation from 🇪🇸 to 🇪🇬:\n\n```\n{translation}```",parse_mode='Markdown')
                            return
                bot.reply_to(message.reply_to_message,  f"{message.from_user.first_name}, here's your translation from {from_lang.upper()} to AR:\n\n```\n{translation}```",parse_mode='Markdown')
                return
        elif message.reply_to_message is None:
            print('checking if message doesnt have reply')
            if len(message.text.split()) > 1:
                text_to_trans = message.text.split('\n')
                text_to_trans[0] = ' '.join(text_to_trans[0].split()[1:])
                text_to_trans='\n'.join(text_to_trans)
                translation = gtrans.translate(text_to_trans, dest=to_lang).text
                if from_lang is None:
                    from_lang = gtrans.detect(text_to_trans).lang
                try:
                    if isinstance(from_lang, list) and any(isinstance(item, str) for item in from_lang): # if this is a list and any of the items are str items not chr items
                        from_lang = from_lang[0]
                except: pass
                bot.reply_to(message,  f"{message.from_user.first_name}, here's your translation from {from_lang.upper()} to AR:\n\n```\n{translation}```",parse_mode='Markdown')
    except:
        pass

def check_en_es(message):
    return message.text.lower().split()[0] in ("en-es", "🇬🇧 🇪🇸", "🇬🇧🇪🇸") or (message.text.split()[0].replace(message.text[0],"").lower() in ("en-es", "enes") and not message.text.lower().split()[0][0].isalpha())
@bot.message_handler(func=check_en_es)
def translate_en_es(message):
    from_lang = 'en'
    to_lang = 'es'
    print('ENTERED', from_lang, to_lang)
    if message.reply_to_message is None and not len(message.text.split()) > 1:
        print("line 467 en es")
        bot_reply_msg = bot.send_message(message.chat.id, f"{message.from_user.first_name}, please reply to this message with the English text or voice note you wish to translate to Spanish", reply_markup=telebot.types.ForceReply(selective=True), reply_to_message_id=message.message_id)
        bot.register_for_reply(bot_reply_msg, handle_trans_reply, to_lang, flag_msg=message, from_lang=from_lang, from_locale=None, to_locale=None)
        return
    try:
        if message.reply_to_message is not None: # if this has a reply
            if message.reply_to_message.content_type == 'text': # to text 
                text_to_trans = message.reply_to_message.text
                translation = gtrans.translate(text=text_to_trans, src=from_lang ,dest=to_lang).text
                if from_lang is None:
                    from_lang = gtrans.detect(text_to_trans).lang
                try:
                    if isinstance(from_lang, list) and any(isinstance(item, str) for item in from_lang): # if this is a list and any of the items are str items not chr items
                        from_lang = from_lang[0]
                except: pass
                print("from lang at line 482:", from_lang)
                bot.reply_to(message.reply_to_message,  f"{message.from_user.first_name}, here's your translation from {from_lang.upper()} to {to_lang.upper()}:\n\n```\n{translation}```",parse_mode='Markdown')
                return
        elif message.reply_to_message is None:
            print('checking if message doesnt have reply')
            if len(message.text.split()) > 1:
                text_to_trans = message.text.split('\n')
                text_to_trans[0] = ' '.join(text_to_trans[0].split()[1:])
                text_to_trans='\n'.join(text_to_trans)
                translation = gtrans.translate(text=text_to_trans, src=from_lang ,dest=to_lang).text
                if from_lang is None:
                    from_lang = gtrans.detect(text_to_trans).lang
                try:
                    if isinstance(from_lang, list) and any(isinstance(item, str) for item in from_lang): # if this is a list and any of the items are str items not chr items
                        from_lang = from_lang[0]
                except: pass
                bot.reply_to(message,  f"{message.from_user.first_name}, here's your translation from {from_lang.upper()} to {to_lang.upper()}:\n\n```\n{translation}```",parse_mode='Markdown')
    except:
        pass

def check_es_en(message):
    return message.text.lower().split()[0] in ("es-en", "🇪🇸 🇬🇧", "🇪🇸🇬🇧") or (message.text.split()[0].replace(message.text[0],"").lower() in ("es-en", "esen", "ingles") and not message.text.lower().split()[0][0].isalpha())
@bot.message_handler(func=check_es_en)
def translate_es_en(message):
    from_lang = 'es'
    to_lang = 'en'
    print('ENTERED', from_lang, to_lang)
    if message.reply_to_message is None and not len(message.text.split()) > 1:
        print("line 510 es en")
        bot_reply_msg = bot.send_message(message.chat.id, f"{message.from_user.first_name}, please reply to this message with the Spanish text or voice note you wish to translate to English", reply_markup=telebot.types.ForceReply(selective=True), reply_to_message_id=message.message_id)
        bot.register_for_reply(bot_reply_msg, handle_trans_reply, to_lang, flag_msg=message, from_lang=from_lang, from_locale=None, to_locale=None)
        return
    try:
        if message.reply_to_message is not None: # if this has a reply
            if message.reply_to_message.content_type == 'text': # to text 
                text_to_trans = message.reply_to_message.text
                translation = gtrans.translate(text=text_to_trans,src=from_lang,dest=to_lang).text
                if from_lang is None:
                    from_lang = gtrans.detect(text_to_trans).lang
                try:
                    if isinstance(from_lang, list) and any(isinstance(item, str) for item in from_lang): # if this is a list and any of the items are str items not chr items
                        from_lang = from_lang[0]
                except: pass
                print("from lang at line 525:", from_lang)
                bot.reply_to(message.reply_to_message,  f"{message.from_user.first_name}, here's your translation from {from_lang.upper()} to {to_lang.upper()}:\n\n```\n{translation}```",parse_mode='Markdown')
                return
        elif message.reply_to_message is None:
            print('checking if message doesnt have reply')
            if len(message.text.split()) > 1:
                text_to_trans = message.text.split('\n')
                text_to_trans[0] = ' '.join(text_to_trans[0].split()[1:])
                text_to_trans='\n'.join(text_to_trans)
                translation = gtrans.translate(text=text_to_trans, src=from_lang ,dest=to_lang).text
                if from_lang is None:
                    from_lang = gtrans.detect(text_to_trans).lang
                try:
                    if isinstance(from_lang, list) and any(isinstance(item, str) for item in from_lang): # if this is a list and any of the items are str items not chr items
                        from_lang = from_lang[0]
                except: pass
                bot.reply_to(message,  f"{message.from_user.first_name}, here's your translation from {from_lang.upper()} to {to_lang.upper()}:\n\n```\n{translation}```",parse_mode='Markdown')
    except:
        pass

# ES - AR (commands are: es-ar, *arabica/arábica, *esar) EASIEST IS: arabica
def check_es_ar(message):
    return message.text.lower().split()[0] in ("es-ar", "🇪🇸 🇪🇬", "🇪🇸🇪🇬") or (message.text.split()[0].replace(message.text[0],"").lower() in ("esar", "arabica", "arábica") and not message.text.lower().split()[0][0].isalpha())
@bot.message_handler(func=check_es_ar)
def translate_es_ar(message):
    from_lang = 'es'
    to_lang = 'ar'
    print('ENTERED', from_lang, to_lang)
    if message.reply_to_message is None and not len(message.text.split()) > 1:
        print("line 554 es en")
        bot_reply_msg = bot.send_message(message.chat.id, f"{message.from_user.first_name}, please reply to this message with the Spanish text or voice note you wish to translate to Arabic", reply_markup=telebot.types.ForceReply(selective=True), reply_to_message_id=message.message_id)
        bot.register_for_reply(bot_reply_msg, handle_trans_reply, to_lang, flag_msg=message, from_lang=from_lang, from_locale=None, to_locale=None)
        return
    try:
        if message.reply_to_message is not None: # if this has a reply
            if message.reply_to_message.content_type == 'text': # to text 
                text_to_trans = message.reply_to_message.text
                translation = gtrans.translate(text=text_to_trans,src=from_lang,dest=to_lang).text
                if from_lang is None:
                    from_lang = gtrans.detect(text_to_trans).lang
                try:
                    if isinstance(from_lang, list) and any(isinstance(item, str) for item in from_lang): # if this is a list and any of the items are str items not chr items
                        from_lang = from_lang[0]
                except: pass
                print("from lang at line 569:", from_lang)
                bot.reply_to(message.reply_to_message,  f"{message.from_user.first_name}, here's your translation from {from_lang.upper()} to {to_lang.upper()}:\n\n```\n{translation}```",parse_mode='Markdown')
                return
        elif message.reply_to_message is None:
            print('checking if message doesnt have reply')
            if len(message.text.split()) > 1:
                text_to_trans = message.text.split('\n')
                text_to_trans[0] = ' '.join(text_to_trans[0].split()[1:])
                text_to_trans='\n'.join(text_to_trans)
                translation = gtrans.translate(text=text_to_trans, src=from_lang ,dest=to_lang).text
                if from_lang is None:
                    from_lang = gtrans.detect(text_to_trans).lang
                try:
                    if isinstance(from_lang, list) and any(isinstance(item, str) for item in from_lang): # if this is a list and any of the items are str items not chr items
                        from_lang = from_lang[0]
                except: pass
                bot.reply_to(message,  f"{message.from_user.first_name}, here's your translation from {from_lang.upper()} to {to_lang.upper()}:\n\n```\n{translation}```",parse_mode='Markdown')
    except:
        pass

def check_ar_es(message):
    return message.text.lower().split()[0] in ("ar-es", "🇪🇬 🇪🇸", "🇪🇬🇪🇸") or (message.text.split()[0].replace(message.text[0],"").lower() in ("ares", "سباني", "اسباني", "س") and not message.text.lower().split()[0][0].isalpha())
@bot.message_handler(func=check_ar_es)
def translate_ar_es(message):
    from_lang = 'ar'
    to_lang = 'es'
    print('ENTERED', from_lang, to_lang)
    if message.reply_to_message is None and not len(message.text.split()) > 1:
        print("line 597 es en")
        bot_reply_msg = bot.send_message(message.chat.id, f"{message.from_user.first_name}, please reply to this message with the Arabic text or voice note you wish to translate to Spanish", reply_markup=telebot.types.ForceReply(selective=True), reply_to_message_id=message.message_id)
        bot.register_for_reply(bot_reply_msg, handle_trans_reply, to_lang, flag_msg=message, from_lang=from_lang, from_locale=None, to_locale=None)
        return
    try:
        if message.reply_to_message is not None: # if this has a reply
            if message.reply_to_message.content_type == 'text': # to text 
                text_to_trans = message.reply_to_message.text
                translation = gtrans.translate(text=text_to_trans,src=from_lang,dest=to_lang).text
                if from_lang is None:
                    from_lang = gtrans.detect(text_to_trans).lang
                try:
                    if isinstance(from_lang, list) and any(isinstance(item, str) for item in from_lang): # if this is a list and any of the items are str items not chr items
                        from_lang = from_lang[0]
                except: pass
                print("from lang at line 612:", from_lang)
                bot.reply_to(message.reply_to_message,  f"{message.from_user.first_name}, here's your translation from {from_lang.upper()} to {to_lang.upper()}:\n\n```\n{translation}```",parse_mode='Markdown')
                return
        elif message.reply_to_message is None:
            print('checking if message doesnt have reply')
            if len(message.text.split()) > 1:
                text_to_trans = message.text.split('\n')
                text_to_trans[0] = ' '.join(text_to_trans[0].split()[1:])
                text_to_trans='\n'.join(text_to_trans)
                translation = gtrans.translate(text=text_to_trans, src=from_lang ,dest=to_lang).text
                if from_lang is None:
                    from_lang = gtrans.detect(text_to_trans).lang
                try:
                    if isinstance(from_lang, list) and any(isinstance(item, str) for item in from_lang): # if this is a list and any of the items are str items not chr items
                        from_lang = from_lang[0]
                except: pass
                bot.reply_to(message,  f"{message.from_user.first_name}, here's your translation from {from_lang.upper()} to {to_lang.upper()}:\n\n```\n{translation}```",parse_mode='Markdown')
    except:
        pass

def check_ar_en(message):
    return message.text.lower().split()[0] in ("ar-en", "🇪🇬 🇬🇧", "🇪🇬🇬🇧") or (message.text.split()[0].replace(message.text[0],"").lower() in ("aren", "ن", "انجليزي", "نجليزي") and not message.text.lower().split()[0][0].isalpha())
@bot.message_handler(func=check_ar_en)
def translate_ar_en(message):
    from_lang = 'ar'
    to_lang = 'en'
    print('ENTERED', from_lang, to_lang)
    if message.reply_to_message is None and not len(message.text.split()) > 1:
        print("line 640 es en")
        bot_reply_msg = bot.send_message(message.chat.id, f"{message.from_user.first_name}, please reply to this message with the Arabic text or voice note you wish to translate to English", reply_markup=telebot.types.ForceReply(selective=True), reply_to_message_id=message.message_id)
        bot.register_for_reply(bot_reply_msg, handle_trans_reply, to_lang, flag_msg=message, from_lang=from_lang, from_locale=None, to_locale=None)
        return
    try:
        if message.reply_to_message is not None: # if this has a reply
            if message.reply_to_message.content_type == 'text': # to text 
                text_to_trans = message.reply_to_message.text
                translation = gtrans.translate(text=text_to_trans,src=from_lang,dest=to_lang).text
                if from_lang is None:
                    from_lang = gtrans.detect(text_to_trans).lang
                try:
                    if isinstance(from_lang, list) and any(isinstance(item, str) for item in from_lang): # if this is a list and any of the items are str items not chr items
                        from_lang = from_lang[0]
                except: pass
                print("from lang at line 655:", from_lang)
                bot.reply_to(message.reply_to_message,  f"{message.from_user.first_name}, here's your translation from {from_lang.upper()} to {to_lang.upper()}:\n\n```\n{translation}```",parse_mode='Markdown')
                return
        elif message.reply_to_message is None:
            print('checking if message doesnt have reply')
            if len(message.text.split()) > 1:
                text_to_trans = message.text.split('\n')
                text_to_trans[0] = ' '.join(text_to_trans[0].split()[1:])
                text_to_trans='\n'.join(text_to_trans)
                translation = gtrans.translate(text=text_to_trans, src=from_lang ,dest=to_lang).text
                if from_lang is None:
                    from_lang = gtrans.detect(text_to_trans).lang
                try:
                    if isinstance(from_lang, list) and any(isinstance(item, str) for item in from_lang): # if this is a list and any of the items are str items not chr items
                        from_lang = from_lang[0]
                except: pass
                bot.reply_to(message,  f"{message.from_user.first_name}, here's your translation from {from_lang.upper()} to {to_lang.upper()}:\n\n```\n{translation}```",parse_mode='Markdown')
    except:
        pass

# EN - AR (commands are: en-ar, *enar) EASIEST IS: *enar
def check_en_ar(message):
    return (message.text.lower().split()[0] in ("en-ar", "🇬🇧 🇪🇬", "🇬🇧🇪🇬") ) or ( message.text.split()[0].replace(message.text[0],"").lower() == "enar" and not message.text.lower().split()[0][0].isalpha() )
@bot.message_handler(func=check_en_ar)
def translate_en_ar(message):
    from_lang = 'en'
    to_lang = 'ar'
    print('ENTERED', from_lang, to_lang)
    if message.reply_to_message is None and not len(message.text.split()) > 1:
        print("line 684 es en")
        bot_reply_msg = bot.send_message(message.chat.id, f"{message.from_user.first_name}, please reply to this message with the English text or voice note you wish to translate to Arabic", reply_markup=telebot.types.ForceReply(selective=True), reply_to_message_id=message.message_id)
        bot.register_for_reply(bot_reply_msg, handle_trans_reply, to_lang, flag_msg=message, from_lang=from_lang, from_locale=None, to_locale=None)
        return
    try:
        if message.reply_to_message is not None: # if this has a reply
            if message.reply_to_message.content_type == 'text': # to text 
                text_to_trans = message.reply_to_message.text
                translation = gtrans.translate(text=text_to_trans,src=from_lang,dest=to_lang).text
                if from_lang is None:
                    from_lang = gtrans.detect(text_to_trans).lang
                try:
                    if isinstance(from_lang, list) and any(isinstance(item, str) for item in from_lang): # if this is a list and any of the items are str items not chr items
                        from_lang = from_lang[0]
                except: pass
                print("from lang at line 699:", from_lang)
                bot.reply_to(message.reply_to_message,  f"{message.from_user.first_name}, here's your translation from {from_lang.upper()} to {to_lang.upper()}:\n\n```\n{translation}```",parse_mode='Markdown')
                return
        elif message.reply_to_message is None:
            print('checking if message doesnt have reply')
            if len(message.text.split()) > 1:
                text_to_trans = message.text.split('\n')
                text_to_trans[0] = ' '.join(text_to_trans[0].split()[1:])
                text_to_trans='\n'.join(text_to_trans)
                translation = gtrans.translate(text=text_to_trans, src=from_lang ,dest=to_lang).text
                if from_lang is None:
                    from_lang = gtrans.detect(text_to_trans).lang
                try:
                    if isinstance(from_lang, list) and any(isinstance(item, str) for item in from_lang): # if this is a list and any of the items are str items not chr items
                        from_lang = from_lang[0]
                except: pass
                bot.reply_to(message,  f"{message.from_user.first_name}, here's your translation from {from_lang.upper()} to {to_lang.upper()}:\n\n```\n{translation}```",parse_mode='Markdown')
    except:
        pass

def generate_choose_language_markup():
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

@bot.message_handler( func=lambda message: message.text.split()[0].replace(message.text[0],"").lower() in ("t", "translate", "ت") and not message.text.lower().split()[0][0].isalpha() and message.reply_to_message is None)
def bot_reply_choose_lang(message):
    global global_t_msg
    #bot.reply_to(message, choose_language_txt, reply_markup=generate_choose_language_markup())
    bot.send_message(message.chat.id, choose_language_txt, reply_markup=generate_choose_language_markup(), reply_to_message_id=message.message_id)
    global_t_msg = message
    print('t_msg is:', global_t_msg)
    bot.register_for_reply(message, translate_two_flags, message)

@bot.callback_query_handler(lambda call: call.message.reply_to_message.content_type != "voice")
def choose_language_callback_query(call):
    text_to_trans = " ".join(call.message.reply_to_message.text.split()[1:])
    if text_to_trans:
        from_lang = gtrans.detect(text_to_trans).lang
        if isinstance(from_lang, list) and any(isinstance(item, str) for item in from_lang): # if this is a list and any of the items are str items not chr items
            from_lang = from_lang[0]
        print("from lang at line 750:", from_lang)
    to_lang = "es"
    print("to_lang at line 752", to_lang)
    match call.data:
        case "cb_es":
            translation = gtrans.translate(text=text_to_trans, dest='es').text
            to_lang = "es"
            to_locale = 'es-ES'
        case "cb_en":
            translation = gtrans.translate(text=text_to_trans, dest='en').text
            to_lang = "en"
            to_locale = 'en-GB'
        case "cb_ar":
            translation = gtrans.translate(text=text_to_trans, dest='ar').text
            to_lang = "ar"
            to_locale = 'ar-EG'
        case "cb_ja":
            translation = gtrans.translate(text=text_to_trans, dest='ja').text
            to_lang = "ja"
            to_locale = 'ja-JO'
        case "cb_ko":
            translation = gtrans.translate(text=text_to_trans, dest='ko').text
            to_lang = "ko"
            to_locale = 'ko-KO'
        case "cb_fr":
            translation = gtrans.translate(text=text_to_trans, dest='fr').text
            to_lang = "fr"
            to_locale = 'fr-FR'
    if call.message.reply_to_message.text.split()[0].replace(call.message.reply_to_message.text[0],"").lower() in ("t", "translate", "ت") and len(call.message.reply_to_message.text.split()) > 1:
        bot.reply_to(call.message.reply_to_message, f"{call.message.reply_to_message.from_user.first_name}, here's your translation from {from_lang.upper()} to {to_lang.upper()}:\n\n```\n{translation}```",parse_mode='Markdown')
        bot.delete_message(call.message.chat.id, call.message.id)
    else:
        print("line 782")
        bot_reply_msg = bot.send_message(call.message.chat.id, f"{call.message.reply_to_message.from_user.first_name}, please reply to this message with the text or voice note you wish to translate to {to_lang.upper()}", reply_markup=telebot.types.ForceReply(selective=True), reply_to_message_id=call.message.reply_to_message.message_id)
        #bot_reply_msg = bot.reply_to(call.message.reply_to_message, f"{call.message.reply_to_message.from_user.first_name}, Reply to this message with the text you wish to translate to {to_lang.upper()}")
        bot.delete_message(call.message.chat.id, call.message.id)
        bot.delete_message(call.message.reply_to_message.chat.id, call.message.reply_to_message.message_id)
        bot.register_for_reply(bot_reply_msg, handle_trans_reply, to_lang, flag_msg=None, from_lang=None, from_locale=None, to_locale=to_locale)

def handle_trans_reply(message, to_lang, flag_msg, from_lang, from_locale, to_locale):
    print("entered handle trans reply")
    print("to_lang at line 791:", to_lang)
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
            print("replied to bot with voice note")
            try:
                trans_voice_results = translate_voice_message(message.reply_to_message, from_lang, to_lang, from_locale, to_locale)
                ogg_file, wav_file = trans_voice_results[0], trans_voice_results[1]
            finally:
                delete_sound_files(ogg_file, wav_file)
            
        if flag_msg:
            if flag_msg.reply_to_message: # choose a language text
                bot.delete_message(message.chat.id, flag_msg.reply_to_message.message_id)
            bot.delete_message(message.chat.id, flag_msg.message_id)


def translate_voice_message(message:telebot.types.Message, from_lang, to_lang, from_locale, to_locale):

    voice_note_file_path = bot.get_file(message.voice.file_id).file_path
    print('voice_note_file_path:', voice_note_file_path)

    #bot.reply_to(message, "`Sorry! Bot currently doesn't fully support voice-note translation on the host site.`",parse_mode="Markdown")
    #return # currently the host site can't run the speech sdk

    voice_data = bot.download_file(voice_note_file_path)

    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    voice_note_file_path = f"voice_note.ogg_{timestamp}"
    wav_file_name = f'voice_note.wav_{timestamp}'
    
    with open(voice_note_file_path, 'wb') as voice_file:
        voice_file.write(voice_data)
        
    # Convert the voice note to a format recognized by the speech recognition library
    raw_audio = AudioSegment.from_file(voice_note_file_path, format="ogg")

    segments = silence.detect_nonsilent(raw_audio, silence_thresh=-40, min_silence_len=200, seek_step=1) 
    audio = AudioSegment.silent() 
    for start, end in segments:
        audio += raw_audio[start:end]

    

    audio.export(wav_file_name, format="wav")
    
    audio_config = speechsdk.audio.AudioConfig(filename=wav_file_name)
    transcription=None
    speech_config = speechsdk.SpeechConfig(subscription='a72af3632e1e4ae3826210e3c76b56d9', region='westeurope')
    # List of supported locales
    locales_2 = ['en-US', 'es-ES','ar-AE', 'fr-FR','ja-JP', 'zh-CN', 'hi-IN', 'id-ID', 'pt-BR', 'ru-RU', 'bn-IN', 'vi-VN', 'ur-IN', 'de-DE', 'ko-KR', 'it-IT', 'tr-TR', 'ta-IN', 'fil-PH', 'pl-PL', 'uk-UA', 'ro-RO', 'nl-NL', 'th-TH', 'el-GR', 'cs-CZ', 'hu-HU', 'sv-SE', 'he-IL', 'ms-MY', 'ml-IN', 'te-IN', 'da-DK', 'fi-FI', 'sk-SK', 'nb-NO', 'zh-CN-shandong', 'yue-CN', 'zh-CN-sichuan', 'zh-HK', 'zh-TW', 'zu-ZA', 'ca-ES', 'my-MM', 'is-IS', 'lv-LV', 'lt-LT', 'mk-MK', 'si-LK', 'sl-SI', 'sq-AL', 'hy-AM', 'eu-ES', 'hr-HR', 'sr-RS', 'bs-BA', 'ka-GE', 'kk-KZ', 'mt-MT', 'km-KH', 'kn-IN', 'lo-LA', 'mr-IN', 'mn-MN', 'ne-NP', 'ps-AF', 'pa-IN', 'en-ZA', 'gl-ES', 'gu-IN', 'it-CH', 'jv-ID', 'nl-BE', 'pt-PT', 'sw-KE', 'sw-TZ', 'af-ZA', 'am-ET', 'ar-BH', 'ar-DZ', 'ar-EG', 'ar-IL', 'ar-IQ', 'ar-JO', 'ar-KW', 'ar-LB', 'ar-LY', 'ar-MA', 'ar-OM', 'ar-PS', 'ar-QA', 'ar-SA', 'ar-SY', 'ar-TN', 'ar-YE', 'az-AZ', 'bg-BG', 'cy-GB', 'de-AT', 'de-CH', 'en-AU', 'en-CA', 'en-GB', 'en-GH', 'en-HK', 'en-IE', 'en-IN', 'en-KE', 'en-NG', 'en-NZ', 'en-PH', 'en-SG', 'en-TZ', 'es-AR', 'es-BO', 'es-CL', 'es-CO', 'es-CR', 'es-CU', 'es-DO', 'es-EC', 'es-GQ', 'es-GT', 'es-HN', 'es-MX', 'es-NI', 'es-PA', 'es-PE', 'es-PR', 'es-PY', 'es-SV', 'es-US', 'es-UY', 'es-VE', 'et-EE', 'fa-IR', 'fr-BE', 'fr-CA', 'fr-CH', 'ga-IE', 'so-SO', 'uz-UZ', 'wuu-CN']



    if from_lang is None:
        print("NO FROM LANG PROVIDED, USING THE AUTO CONFIG")
        grouped_locales = [locales_2[i:i+4] for i in range(0, len(locales_2), 4)]

        # Create language configurations for each set
        lang_configs = []

        for group in grouped_locales:
            lang_configs.append([speechsdk.languageconfig.SourceLanguageConfig(lang) for lang in group])

        # Create AutoDetectSourceLanguageConfig instances
        auto_detect_configs = [speechsdk.languageconfig.AutoDetectSourceLanguageConfig(sourceLanguageConfigs=group) for group in lang_configs]

        # Use the configurations in the speech recognizer
        for auto_detect_config in auto_detect_configs:
            print("current auto det config:", auto_detect_config)
            speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, auto_detect_source_language_config=auto_detect_config, audio_config=audio_config)
            result = speech_recognizer.recognize_once()
            try:
                if isinstance(gtrans.detect(result.text).confidence, list):
                    if gtrans.detect(result.text).confidence[0] > 0.81:
                        break
                else:
                    if gtrans.detect(result.text).confidence > 0.81:
                        break
            except:
                pass

    else:
        print("from_locale is", from_locale)
        if (from_locale == 'en' and from_lang) or (from_locale is None and from_lang):
            print("from_locale is None")
            match from_lang:
                case 'ar': from_locale = 'ar-EG'
                case 'en': from_locale = 'en-US'
                case 'es': from_locale = 'es-ES'
        print("FROM LANG PROVIDED, USING THAT LOCALE", from_locale)
        speech_recognizer = speechsdk.SpeechRecognizer(speech_config, language=from_locale,audio_config=audio_config)
        result = speech_recognizer.recognize_once()


    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        auto_detect_result = speechsdk.AutoDetectSourceLanguageResult(result)
        transcription = result.text
        recognized_lang = auto_detect_result.language
        print("Recognized: {} in language {}".format(transcription, recognized_lang))


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
    print('TO LANGI S', to_lang)
    print(from_lang)
    if isinstance(from_lang, list):
        from_lang = from_lang[0]
    det = gtrans.detect(transcription)
    print("GTRANS DETECTION: ", det)

    if to_lang is None:
        return

    translation = gtrans.translate(transcription, src=from_lang, dest=to_lang)
    print(transcription,translation.text)
    print('recognized lang is:', recognized_lang,"from and to locale are:", from_locale, to_locale, "from and to lang are:", from_lang, to_lang)
    if to_locale != 'en':
        print('1')

        if from_locale is None and recognized_lang is None:
            match from_lang:
                case 'en':
                    from_lang = 'en-GB'
                case 'ar':
                    from_lang = 'ar-EG'
                case 'es':
                    from_lang = 'es-ES'

        if to_locale is None and to_lang is not None:
            try:
                to_locale = get_locale_from_country_code(to_lang)
            except: pass
            match to_lang:
                case 'ar':
                    to_lang = 'ar-EG'
                case 'en':
                    to_lang = 'en-GB'
                case 'es':
                    to_lang = 'es-ES'
            to_locale = to_lang


        if to_lang and to_locale is None:
            match to_lang:
                case 'ar':
                    to_lang = 'ar-EG'
                case 'en':
                    to_lang = 'en-GB'
                case 'es':
                    to_lang = 'es-ES'
        if recognized_lang is None and from_locale is not None:
            recognized_lang = from_locale
        if from_locale is None and recognized_lang is None:
            recognized_lang = from_lang
        bot.reply_to(message, f"\n`Translated from {recognized_lang}:````\n{transcription}```\n`into {to_locale}:`\n```\n{translation.text}```\n",parse_mode="Markdown")
    else:
        print('3')
        if from_locale == 'en':
            if recognized_lang is not None:
                from_lang = recognized_lang
        else:
            from_lang = from_locale
        match to_lang:
            case 'ar':
                to_lang = 'ar-EG'
            case 'en':
                to_lang = 'en-GB'
            case 'es':
                to_lang = 'es-ES'
        bot.reply_to(message, f"\n`Translated from {from_lang}:````\n{transcription}```\n`into {to_lang}:`\n```\n{translation.text}```\n",parse_mode="Markdown")
    return voice_note_file_path, wav_file_name

keep_alive()
bot.polling(none_stop=True)

