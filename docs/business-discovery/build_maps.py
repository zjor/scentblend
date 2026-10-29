"""Build self-contained, editable SVG discovery maps; Python standard library only."""
from pathlib import Path
from html import escape
import textwrap

OUT = Path(__file__).resolve().parent

def n(label, *children):
    return {'label': label, 'children': list(children)}

original = n('Чек-ап',
 n('Общее',
  n('Какой у вас бизнес? История, продукт'), n('Сколько сотрудников работает?'), n('Какие цифры?'),
  n('Организационная структура компании?',
   n('Сколько времени собственники уделяют проекту? Какой функционал у собственника?', n('Есть ли ассистент у руководителя?')),
   n('Сколько руководителей?', n('С чем руководители справляются хорошо?'), n('С чем руководители, на ваш взгляд, справляются плохо?')),
   n('Как распределена ответственность в компании?')),
  n('На ваш взгляд, какие точки роста у компании?')),
 n('Отдел продаж',
  n('Команда', n('Есть ли РОП?'), n('Сколько менеджеров работает?'), n('Есть ли лидогенератор?'), n('Какая оплата у менеджеров и РОПа?')),
  n('Финансовые результаты отдела продаж'),
  n('Опишите воронку продаж', n('Как происходит коммуникация с клиентами?')),
  n('Есть ли база недозвонов?', n('Сколько времени тратит команда на недозвоны?')),
  n('Сколько человек в клиентской базе?'), n('Есть ли квалификация лидов?'),
  n('Есть ли отдел контроля качества?', n('Какой бюджет по зарплате?'), n('Какие задачи выполняют сотрудники?')),
  n('Как работаете с LTV (жизненным циклом) клиентов?')),
 n('Маркетинг',
  n('Команда', n('На какие отделы подразделяется отдел маркетинга?'), n('Сколько сотрудников в каждом отделе?'), n('Фонд заработной платы сотрудников ОМ?')),
  n('Какой функционал у отдела маркетинга?'),
  n('СММ', n('Сколько каналов связи с клиентами: Инстаграм, Телеграм, Ютуб?'), n('Какой объём работы?'), n('Насколько эффективно обрабатываются сообщения в директе и комментарии?')),
  n('Реклама', n('Из каких источников?'), n('Какой объём работ: съёмка видео, тексты, креативы?')),
  n('SEO', n('Продвигаетесь ли через SEO?'), n('Какие результаты?'), n('Кто пишет статьи?')),
  n('Сколько человек в маркетинговой базе клиентов?')),
 n('Продукт', n('Есть ли продуктовая линейка?'),
  n('Кто занимается созданием продукта?', n('Сколько времени уходит?'), n('Какая команда обслуживает создание продукта?')),
  n('Есть ли сложности со съёмками видео? Если да, то какие?'),
  n('Замеряется ли NPS (степень удовлетворённости клиентов продуктом)? Если да, то как часто?')),
 n('Команда (HR)', n('Есть ли внутренние записанные обучения для сотрудников?'),
  n('Как часто сотрудники приходят к руководителям с вопросами? Насколько самостоятельна команда?'), n('Как часто нанимаете сотрудников?')),
 n('Служба поддержки', n('Сколько сотрудников?'), n('Сколько запросов в день обрабатывают сотрудники?'), n('Где идёт коммуникация с клиентами: Инстаграм, Телеграм, почта?')))

adapted = n('Scent Blend',
 n('01  Direction & model',
  n('Business lines & outcomes', n('Which lines are active: space scenting, private label, distribution, brand experiences, B2C shop?'), n('What should change in 12 months? Which three outcomes define success, and from what baseline?')),
  n('Customers & value', n('Who buys, who pays, and who uses each offer? What problem do they pay us to solve?'), n('What counts as a customer: legal entity, brand, group, contact or site? How are these linked?')),
  n('Strategic choices', n('Which segments and offers deserve focus? What will we stop, and what constraint limits growth?'))),
 n('02  People & decisions',
  n('Roles & ownership', n('Who owns sales, scent design, sourcing, installation, service, finance and the shop? Employees or partners?'), n('Where does the owner spend time? Which decisions require approval, and who is the backup?')),
  n('Capacity & knowledge', n('What workload can each role handle? Which skills, incentives or missing instructions create bottlenecks?'), n('How are people hired and trained? Which questions repeatedly come back to the owner?')),
  n('Handoffs & accountability', n('At each handoff, who accepts the work, what must be complete, and where is responsibility recorded?'))),
 n('03  Demand & sales',
  n('Acquisition & qualification', n('Which channels bring qualified B2B enquiries and B2C orders? Who handles messages and follow-ups?'), n('What qualifies a lead: segment, site size, need, budget, decision-maker or timing? Where is it recorded?')),
  n('Enquiry → agreement', n('Walk through a recent sale: enquiry, analysis, scent proposal, trial if any, quote and signed agreement.'), n('Who owns each stage? What are conversion, elapsed time and loss reasons? Is the 24-hour reply promise met?')),
  n('Renewal & expansion', n('How are renewals, cancellations and additional sites identified? Who owns retention and follow-up?'), n('Which opportunities are signed, proposed or only possible? What is the next action and decision date?'))),
 n('04  Offers & production',
  n('Catalogue & commercial terms', n('What is a product, SKU, scent recipe, service package and custom project? Which versions must be tracked?'), n('What is sold, rented or loaned? What do recurring fees include: equipment, refills, visits or replacement?')),
  n('Custom work & suppliers', n('Trace a private-label order: brief, sample approval, recipe, packaging, purchasing, production and delivery.'), n('Who owns recipes and approvals? What are minimum orders, lead times, supplier dependencies and rework causes?')),
  n('Quality & economics', n('How are batches, quality checks and supporting product documents linked? Who resolves a failed batch?'), n('What are price, direct cost and contribution by offer? How are satisfaction and repeat purchases measured?'))),
 n('05  Delivery & service',
  n('Site & installed equipment', n('Trace a new site from signed agreement to installation and acceptance. Who schedules and performs the work?'), n('Which device is at which site, with what scent and settings? Who owns it, and how is its history recorded?')),
  n('Stock & replenishment', n('How are refills and visits triggered? Who plans routes, stock, purchasing and supplier follow-up?'), n('What happens when stock runs out, a device fails, a site moves or a contract ends?')),
  n('Support & fulfilment', n('Trace one complaint: channel, ticket, priority, owner, resolution, cost and customer confirmation.'), n('Trace one shop order: payment, stock allocation, shipment, delivery, return or refund. Which systems exchange data?'))),
 n('06  Money & evidence',
  n('Contract → invoice → cash', n('Who invoices each service period or milestone? How are invoices linked to contracts, sites and payments?'), n('How are deposits, partial payments, overdue invoices, VAT and CZK/EUR amounts distinguished?')),
  n('Revenue, cost & cash', n('What is recurring contracted revenue versus one-off sales and pipeline? How are annual fees allocated by period?'), n('Which records explain margin and cash: invoices, inventory, delivery costs, unpaid bills, other accounts and owner funding?')),
  n('Reconciliation gaps', n('Can we connect Stripe orders, fees, refunds and payouts? A bank payout alone does not identify a buyer.'), n('Reconcile AURES/Mototechna scope, Clever/CodeClever identity and invoice-period differences before combining records.'))),
 n('07  Data & next actions',
  n('Entities & relationships', n('Validate: entity → sites → installed devices; agreement → service lines; order → items; invoice ↔ payments.'), n('For every object: definition, unique ID, owner, key fields, statuses, source of truth and links. What is missing?')),
  n('Process & system map', n('For each workflow: trigger → steps → owner → handoff → output. Capture rules, exceptions, tools and delays.'), n('Where are duplicate entries or manual transfers? Which system is authoritative when records disagree?')),
  n('Close with decisions', n('Select three problems by impact and effort. Assign an owner, next action, due date and success measure.'), n('Separate confirmed facts, hypotheses and unknowns. For each unknown, name the evidence and who will obtain it.'))))

# Fixed column widths and conservative wrapping preserve editable text without external fonts.
XS = [48, 330, 674, 1124, 1650]
WS = [226, 282, 388, 464, 420]
COLORS = ['#245749','#356d80','#85613e','#705982','#477858','#93624b','#4c677b']

def layout(node, depth=0):
    node['depth'] = depth
    node['lines'] = textwrap.wrap(node['label'], width=int((WS[depth]-36)/(21*.59)), break_long_words=False)
    node['box_h'] = max(58, 28 * len(node['lines']) + 26)
    for child in node['children']: layout(child, depth+1)
    node['height'] = max(node['box_h'], sum(c['height'] for c in node['children']) + 16 * max(0, len(node['children'])-1))
    if depth == 1: node['height'] += 42

def place(node, top, color='#245749'):
    node['y'] = top + node['height']/2
    node['color'] = color
    child_top = top + (node['height'] - sum(c['height'] for c in node['children']) - 16 * max(0,len(node['children'])-1))/2
    for i,c in enumerate(node['children']):
        place(c, child_top, COLORS[i % len(COLORS)] if node['depth']==0 else color)
        child_top += c['height']+16

def render(root, filename, title, subtitle, note, footer, edition='Scent Blend · Business discovery · 30 October 2026', description='All labels are editable vector text.'):
    layout(root); place(root, 260)
    width = max(XS[x['depth']]+WS[x['depth']] for x in walk(root))+48
    height = root['height']+420
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
      f'<title id="title">{escape(title)}</title><desc id="desc">{escape(subtitle)} {escape(description)}</desc>',
      '<style>text{font-family:Arial,Helvetica,sans-serif} .label{font-size:21px} .edge{fill:none;stroke-width:2;stroke-opacity:.42}</style>',
      f'<rect width="{width}" height="{height}" fill="#f7f8f3"/>',
      f'<path d="M48 54 H136" stroke="#245749" stroke-width="6"/>',
      f'<text x="48" y="101" font-size="40" font-weight="700" fill="#183d34">{escape(title)}</text>',
      f'<text x="48" y="143" font-size="21" fill="#51635c">{escape(subtitle)}</text>',
      f'<rect x="48" y="174" width="{width-96}" height="54" rx="12" fill="#e7ede4"/>',
      f'<text x="68" y="208" font-size="19" fill="#294c40">{escape(note)}</text>']
    for node in walk(root):
        d=node['depth']
        for c in node['children']:
            x1=XS[d]+WS[d]; x2=XS[d+1]; mid=(x1+x2)/2
            parts.append(f'<path class="edge" stroke="{c["color"]}" d="M{x1} {node["y"]} C{mid} {node["y"]} {mid} {c["y"]} {x2} {c["y"]}"/>')
    for node in walk(root):
        d=node['depth']; x=XS[d]; y=node['y']-node['box_h']/2
        dark=d<2; fill=node['color'] if dark else ('#e8eee6' if node['children'] else '#ffffff')
        if not dark and node.get('status'):
            fill = {'context': '#e3efe9', 'claim': '#fff0d8', 'notes': '#e6edf6'}[node['status']]
        parts.append(f'<g><rect x="{x}" y="{y}" width="{WS[d]}" height="{node["box_h"]}" rx="12" fill="{fill}" stroke="{node["color"]}" stroke-opacity="{0 if dark else .22}"/>')
        for i,line in enumerate(node['lines']):
            parts.append(f'<text class="label" x="{x+18}" y="{y+29+28*i}" fill="{"#ffffff" if dark else "#243b33"}" font-weight="{700 if dark or node["children"] else 400}">{escape(line)}</text>')
        parts.append('</g>')
    parts.extend([f'<path d="M48 {height-105} H{width-48}" stroke="#c8d2c8"/>', f'<text x="48" y="{height-66}" font-size="17" fill="#596b62">{escape(footer)}</text>',f'<text x="48" y="{height-35}" font-size="17" fill="#596b62">{escape(edition)}</text>', '</svg>'])
    (OUT/filename).write_text('\n'.join(parts)+'\n')
    return width,height

def walk(node):
    yield node
    for c in node['children']: yield from walk(c)

if __name__ == '__main__':
    print('Original:', render(original,'business-checkup-original-ru.svg','Первичная диагностика бизнеса',
      'Чек-ап · Общее / Продажи / Маркетинг / Продукт / Команда / Поддержка',
      'Перерисовано по карте коллеги. Структура и вопросы сохранены; орфография и пунктуация уточнены.',
      'Источник: предоставленное изображение «Первичная диагностика бизнеса». Термин LTV сохранён как в оригинале.'))
    print('Adapted:', render(adapted,'scentblend-discovery-en.svg','Scent Blend / Business discovery',
      'An interview map for discovering people, processes, business objects and strategic constraints.',
      'For each answer: ask for a real example → identify the owner → inspect the record → capture exceptions.',
      'Context: BUSINESS.md, README.md, working customer notes. Questions and proposed relationships require validation.'))
    lines=['# Scent Blend — session question bank', '', 'Session: 30 October 2026. Adapted from the supplied Russian business check-up map and local business context.', '', 'These are discovery questions, not assertions about current operations.', '']
    for c in adapted['children']:
        lines += ['## '+c['label'], '']
        for group in c['children']:
            lines += ['### '+group['label'], '']
            lines += ['- '+q['label'] for q in group['children']]
            lines += ['']
    (OUT/'question-bank.md').write_text('\n'.join(lines))
