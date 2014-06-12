# -*- coding: utf-8 -*-
### Zero based index for numbers 0 to 100.
INDEX_SHE       = 101          # 100s
INDEX_HAJAR     = 102          # 1000s
INDEX_LAKH      = 103          # 100000s
INDEX_CRORE     = 104          # 10000000s
INDEX_RUPAYE    = 105          # Rupaye

number_to_word_in_marathi_lookup_table = [
    "शुन्य",
    "एक",
    "दोन",
    "तीन",
    "चार",
    "पाच",
    "सहा",
    "सात",
    "आठ",
    "नऊ",
    "दहा",
    "अकरा",
    "बारा",
    "तेरा",
    "चौदा",
    "पंधरा",
    "सोळा",
    "सातारा",
    "आठरा",
    "एकोणीस",
    "वीस",
    "एकवीस",
    "बावीस",
    "तेवीस",
    "चोवीस",
    "पंचवीस",
    "सव्वीस",
    "सत्तावीस",
    "अठ्ठावीस",
    "एकोणतीस",
    "तीस",
    "एकतीस",
    "बतीस",
    "तेहेत्तीस",
    "चौतीस",
    "पस्तीस",
    "छत्तीस",
    "सदोतीस",
    "अडोतीस",
    "एकोणचाळीस",
    "चाळीस",
    "एक्केचाळीस",
    "बेचाळीस",
    "त्रेचाळीस",
    "चव्वेचाळीस",
    "पंचेचाळीस",
    "सेहेचाळीस",
    "सत्तेचाळीस",
    "अठ्ठेचाळीस",
    "एकोणपन्नास",
    "पन्नास",
    "एक्कावन",
    "बावन",
    "त्रेपन्न",
    "चोपन्न",
    "पंचावन",
    "छप्पन्न",
    "सत्तावन",
    "अठ्ठावन",
    "एकोणसाठ",
    "साठ",
    "एकसष्ट",
    "बासष्ट",
    "त्रेसष्ट",
    "चौसष्ट",
    "पासष्ट",
    "सहासष्ट",
    "सदुसष्ट",
    "अडूसष्ट",
    "एकोणसत्तर",
    "सत्तर",
    "एकाहत्तर",
    "बाहत्तर",
    "त्र्याहत्तर",
    "चौऱ्याहत्तर",
    "पंचाहत्तर",
    "शहात्तर",
    "सत्याहत्तर",
    "अठ्याहत्तर",
    "एकोणऐंशी",
    "ऐंशी",
    "एक्क्याऐंशी",
    "ब्याऐंशी",
    "त्र्याऐंशी",
    "चौऱ्याऐंशी",
    "पंच्याऐंशी",
    "शहाऐंशी",
    "सत्त्याऐंशी",
    "अठ्ठ्याऐंशी",
    "एकोणनव्वद",
    "नव्वद",
    "एक्क्याण्णव",
    "ब्याण्णव",
    "त्र्याण्णव",
    "चौऱ्याण्णव",
    "पंचाण्णव",
    "शहाण्णव",
    "सत्याण्णव",
    "अठ्ठ्याण्णव",
    "नवव्याण्णव",  # 99
    "शंभर",  # 100
    "शे",  # 101: INDEX_SHE
    "हजार",  # 102: INDEX_HAJAR
    "लाख",  # INDEX_LAKH
    "कोटी",  # INDEX_CRORE
    "रुपये",  # INDEX_RUPAYE
]


## Obtain the word string for given index from number_to_word_in_marathi_lookup_table

def number_to_words_in_marathi(number):
    words_in_marathi = ""

    if number == 0:
        words_in_marathi = number_to_word_in_marathi_lookup_table[0]
        return words_in_marathi

    crores    = int(number / 10000000)
    number    = int(number % 10000000)
    lakhs     = int(number / 100000)
    number    = int(number % 100000)
    thousands = int(number / 1000)
    number    = int(number % 1000)
    hundreds  = int(number / 100)
    reminder  = int(number % 100)

    if crores > 100:
        words_in_marathi += number_to_words_in_marathi(crores)                + " " + number_to_word_in_marathi_lookup_table[INDEX_CRORE] # ""दोनशे कोटी"
    elif crores > 0:
        words_in_marathi += number_to_word_in_marathi_lookup_table[crores]    + " " + number_to_word_in_marathi_lookup_table[INDEX_CRORE] # "दोन कोटी"
    if lakhs  > 0:
        if words_in_marathi != "":
            words_in_marathi += " "
        words_in_marathi += number_to_word_in_marathi_lookup_table[lakhs]     + " " + number_to_word_in_marathi_lookup_table[INDEX_LAKH]  # "दोन लाख"
    if thousands > 0:
        if words_in_marathi != "":
            words_in_marathi += " "
        words_in_marathi += number_to_word_in_marathi_lookup_table[thousands] + " " + number_to_word_in_marathi_lookup_table[INDEX_HAJAR] # "दोन हजार"
    """ Commented till next one
    if ((hundreds > 1) or ((hundreds == 1) and (reminder>0))):
        words_in_marathi += number_to_word_in_marathi_lookup_table[hundreds] + number_to_word_in_marathi_lookup_table[INDEX_SHE] # "दोनशे", "एकशे दोन" -- no space before "she"
    if ((hundreds == 1) and (reminder == 0)):
        words_in_marathi += number_to_word_in_marathi_lookup_table[100] # "शंभर", "दोन हजार शंभर"
    """
    if hundreds > 0:
        if words_in_marathi != "":
            words_in_marathi += " "
        words_in_marathi += number_to_word_in_marathi_lookup_table[hundreds] + number_to_word_in_marathi_lookup_table[INDEX_SHE] # "दोनशे", "एकशे दोन" -- no space before "she"
    if reminder > 0:
        if words_in_marathi != "":
            words_in_marathi += " "
        words_in_marathi += number_to_word_in_marathi_lookup_table[reminder] # "दोन"
    return words_in_marathi

#######################

digit_to_string_in_devnagari_lookup_table = [
    "०",
    "१",
    "२",
    "३",
    "४",
    "५",
    "६",
    "७",
    "८",
    "९"
]

def number_to_string_in_devnagari(number):
    string_in_devnagari = ""
    while True:
        digit  = number % 10
        string_in_devnagari = digit_to_string_in_devnagari_lookup_table[digit] + string_in_devnagari
        number = int(number / 10)
        if number == 0:
            break
    return string_in_devnagari

def convert(number):
    amount = int(number)
    number_string = number_to_string_in_devnagari(amount)
    number_in_words = number_to_words_in_marathi(amount) + " " + number_to_word_in_marathi_lookup_table[INDEX_RUPAYE]
    return number_string, number_in_words