"""A fixed lexical router built from the six ordinary domain definitions."""
import re

TERMS = {
    'coding': 'function|programming|python|javascript|typescript|compiler error|exception|stack trace|parser|algorithm|unit test|debug|database|sql|repository|git|refactor|api|stdlib|variable|loop|library|runtime error|command line|return value',
    'math': 'equation|solve for|integral|derivative|triangle|geometry|proof|prove|fraction|percentage|percent|probability|polynomial|theorem|divisible by|prime number|linear algebra|matrix|arithmetic|median|mean|square root|sequence',
    'physical_science': 'physics|chemistry|gravity|acceleration|velocity|force|energy|temperature|heat|magnet|electric field|voltage|density|pressure|momentum|kinetic|friction|wavelength|photon|molecule|reaction|phase change|experiment|resistance',
    'conversation': 'thank|sorry|apolog|friend|polite|kindly|sympathy|sympathetic|condolence|message to|tell my|awkward|tone|comfort|conversation|small talk|encourage|supportive|listen|colleague|roommate|decline|reassure',
    'machine_learning': 'machine learning|neural|train|classifier|labelled|labeled|gradient|regression|embedding|feature vector|validation set|holdout|overfit|dataset|learning rate|prediction|loss function|fine tuning|precision and recall|confusion matrix|cross validation|hyperparameter',
    'computer_engineering': 'processor|cpu|gpu|pipeline stall|register|cache|memory bus|circuit|clock cycle|fpga|verilog|digital logic|flip flop|microcontroller|firmware|interrupt|instruction set|transistor|hardware|board layout|cache miss|timing closure|sram|bit width',
}
PATTERNS = {domain: [re.compile(r'\b' + term.replace(' ', r'[\s-]+') + r'\w*\b', re.I)
                     for term in terms.split('|')] for domain, terms in TERMS.items()}
CONTEXT = re.compile(r'\b(this|that|those|these|there|they|it|again|previous|same|suggested|first|second|last|mine|one|next)\b', re.I)


def scores(text):
    return {domain: sum(bool(term.search(text)) for term in patterns) for domain, patterns in PATTERNS.items()}


def lead(points):
    highest = max(points.values())
    leaders = [domain for domain, value in points.items() if value == highest]
    return leaders[0] if highest and len(leaders) == 1 else None


def read(message, history=()):
    direct = scores(message)
    if max(direct.values()):
        return lead(direct)
    if CONTEXT.search(message):
        context = ' '.join(row['content'] for row in history[-2:] if row['role'] in ('user', 'assistant'))
        return lead(scores(context))
    return None
