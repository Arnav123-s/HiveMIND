"""An answer is accepted only if the whole prompt and response fit an independently checked contract."""
from decimal import Decimal, localcontext
import math
import re

from team.specialists import writer

MONTH = '(?:' + '|'.join(writer.MONTHS) + ')'
DATE = rf'(?:[0-9]{{1,2}} {MONTH} [0-9]{{4}}|[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}})'
AMOUNT = r'[0-9]{1,8}(?:\.[0-9]{1,2})?'
WEEKDAY = re.compile(rf'(?:what|which) day of the week is ({DATE})\?', re.I)
DAYS = re.compile(rf'how many days (?:are there )?(?:from|between) ({DATE}) (?:to|and) ({DATE})\?', re.I)
GCD = re.compile(r'what is the (?:greatest common divisor|gcd) of ([0-9]{1,12}) and ([0-9]{1,12})\?', re.I)
TEMPERATURE = re.compile(r'what is ([+-]?[0-9]{1,6}(?:\.[0-9]{1,4})?) degrees (celsius|fahrenheit) in (fahrenheit|celsius)\? one decimal place\.', re.I)
PRICE = re.compile(rf'(?:a|an) [a-z]+ costs ({AMOUNT}) dollars and the price (rises|falls) by ([0-9]{{1,2}})%\. what is the new price\?', re.I)


def date(value):
    match = writer.DATE_RX.fullmatch(value)
    return writer._date(match) if match else None


def expected(prompt):
    """Derive the value from the supplied words. Unsupported or ambiguous prompts produce no certificate."""
    if not isinstance(prompt,str) or len(prompt)>260:
        return None
    value = ' '.join(prompt.casefold().split())
    m = WEEKDAY.fullmatch(value)
    if m:
        day = date(m[1])
        return ('weekday',writer.DAYS[day.weekday()]) if day else None
    m = DAYS.fullmatch(value)
    if m:
        start,end=map(date,m.groups())
        return ('days',(end-start).days) if start and end and end>=start else None
    m = GCD.fullmatch(value)
    if m:
        a,b=map(int,m.groups())
        return ('gcd',math.gcd(a,b)) if a and b else None
    m = TEMPERATURE.fullmatch(value)
    if m and m[2]!=m[3]:
        v=Decimal(m[1])
        with localcontext() as ctx:
            ctx.prec=28
            result=(v-32)*5/9 if m[2]=='fahrenheit' else v*9/5+32
            return m[3],result.quantize(Decimal('0.1'))
    m = PRICE.fullmatch(value)
    if m:
        price=Decimal(m[1]);percent=int(m[3])*(1 if m[2]=='rises' else -1)
        result=price*(100+percent)/100
        return ('dollars',result) if result==result.quantize(Decimal('0.01')) else None
    return None


def certify(prompt,answer):
    contract=expected(prompt)
    if contract is None or not isinstance(answer,str) or len(answer)>100:
        return False
    value=' '.join(answer.casefold().strip().split()).removesuffix('.')
    kind,want=contract
    if kind=='weekday':
        return value==want
    if kind in ('gcd','days'):
        unit='(?: days?)?' if kind=='days' else ''
        m=re.fullmatch(rf'(?:{kind}: )?([0-9]{{1,15}}){unit}',value)
        return bool(m and int(m[1])==want)
    if kind=='dollars':
        m=re.fullmatch(rf'(?:new price: )?\$?({AMOUNT})(?: dollars?)?',value)
    else:
        unit='c' if kind=='celsius' else 'f'
        m=re.fullmatch(rf'([+-]?[0-9]{{1,8}}\.[0-9])(?:\s*(?:degrees? |°\s*)?(?:{kind}|{unit}))?',value)
    return bool(m and Decimal(m[1])==want)
