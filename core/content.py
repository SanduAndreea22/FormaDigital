"""Site copy. All figures in CASE_STUDIES are illustrative demo numbers, not real clients."""

SERVICES = [
    {'name': 'SEO', 'price': 'From 2,900 RON / month',
     'text': 'Pages that show up in Google for the searches your customers actually make. Technical audit, content and links.'},
    {'name': 'Paid ads', 'price': 'From 3,500 RON / month',
     'text': 'Google and Meta campaigns with a controlled budget, checked daily. You know exactly what you spend and what you get.'},
    {'name': 'Social media', 'price': 'From 2,400 RON / month',
     'text': 'Posting calendar, design and a monthly report. Content that supports sales, not just presence.'},
]

PACKAGES = [
    {'name': 'Start', 'price': '2,900', 'featured': False,
     'features': ['On-page SEO for 5 pages', 'Monthly ranking report', '1 strategy call per month']},
    {'name': 'Growth', 'price': '5,400', 'featured': True,
     'features': ['Full SEO with links and content', 'Managed Google or Meta campaigns',
                  'Social media, 12 posts per month', 'Weekly report with numbers']},
    {'name': 'Dominance', 'price': '9,800', 'featured': False,
     'features': ['Everything in Growth', 'Multi-channel campaigns',
                  'Social media, 20 posts per month', 'Quarterly strategy with your team']},
]

CASE_STUDIES = [
    {'big': '+184%', 'title': 'Dental clinic (demo) — booking requests',
     'text': 'Local campaign, 6 months.',
     'stats': [('3.1x', 'return on ads'), ('64', 'pages indexed'), ('-22%', 'cost per booking')]},
    {'big': 'x2.4', 'title': 'Online store (demo) — online sales',
     'text': 'SEO and ads, 9 months.',
     'stats': [('2.4x', 'organic traffic'), ('41', 'categories optimised'), ('+37%', 'monthly revenue')]},
]

PROCESS = [
    ('Audit', 'We look at what you have now, what customers search for and where you lose money.'),
    ('Strategy', 'A written plan with objectives and numbers we will measure.'),
    ('Launch', 'We implement, test and adjust during the first 30 days.'),
    ('Reporting', 'A simple monthly report: what worked, what did not, and what we do next.'),
]
