"""Independent mixed calculator/fee questions; run before service inspection or grading."""
import datetime as dt
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_EVEN
import json
from pathlib import Path
import math

def depot(masses):
    return 250 + 90 * sum(int((Decimal(kg) * 2).to_integral_value(rounding=ROUND_CEILING)) for kg in masses)

def weekday(iso):
    return ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")[dt.date.fromisoformat(iso).weekday()]

rows=[]
def add(id,question,group,value=None,unit=None):
    rows.append((dict(id=id,question=question),dict(group=group,value=value,unit=unit)))

add("leap-appointment","Which day of the week is 2040-02-29?","calendar",weekday("2040-02-29"),"weekday")
add("across-year","How many days are there from 2027-12-29 to 2028-01-04?","calendar",(dt.date(2028,1,4)-dt.date(2027,12,29)).days,"days")
add("shared-groups","What is the greatest common divisor of 414 and 690?","arithmetic",math.gcd(414,690),"integer")
add("cold-morning","What is -7.5 degrees Celsius in Fahrenheit? One decimal place.","arithmetic",str((Decimal("-7.5")*9/5+32).quantize(Decimal("0.1"),rounding=ROUND_HALF_EVEN)),"fahrenheit")
add("shop-discount","A notebook costs 28 dollars and the price falls by 25%. What is the new price?","arithmetic",str(Decimal(28)*Decimal("0.75")),"dollars")
add("separate-parcels","Calculate the depot shipping fee for 0.232 kg and 0.161 kg using per-parcel rounding.","shipping-kg",depot(["0.232","0.161"]),"cents")
add("three-parcels","Calculate the depot shipping fee for 0.501 kg and 1.002 kg and 0.005 kg.","shipping-kg",depot(["0.501","1.002","0.005"]),"cents")
add("single-parcel","Calculate the depot shipping fee for 0.740 kg?","shipping-kg",depot(["0.740"]),"cents")
add("boundary-plus","Calculate the depot shipping fee for 0.500 kg and 0.001 kg using per-parcel rounding?","shipping-kg",depot(["0.500","0.001"]),"cents")
add("gram-compatibility","Calculate the depot shipping fee for 187 g and 476 g using per-parcel rounding.","shipping-grams",depot(["0.187","0.476"]),"cents")
add("date-in-conversation","Could you tell me what weekday 2031-10-06 falls on?","paraphrase",weekday("2031-10-06"),"weekday")
add("mailroom-note","At our depot I am sending two parcels weighing 0.284 kg and 0.191 kg. How many cents is the shipping fee if each parcel is rounded separately?","paraphrase",depot(["0.284","0.191"]),"cents")
add("leap-error","Which day of the week is 2031-02-29?","invalid-date")
add("city-date-order","What day of the week is 08/09/2030?","ambiguous-date")
add("mismatched-units","What is 17 degrees Celsius in litres? One decimal place.","incompatible-units")
add("box-not-weighed","Calculate the depot shipping fee for a 0.601 kg parcel including packaging. The depot excludes the packaging but I don't know its weight.","insufficient-weight")
add("missing-tariff","Calculate the depot shipping fee for 1.500 kg using pooled rounding.","unavailable-policy")
add("partial-result","What is the GCD of 286 and 121? Also list every common divisor.","additional-deliverable")
d=Path(__file__).resolve().parent
(d/'panel.json').write_text(json.dumps([r[0] for r in rows],indent=2)+'\n')
(d/'keys.json').write_text(json.dumps({r[0]['id']:r[1] for r in rows},indent=2)+'\n')
