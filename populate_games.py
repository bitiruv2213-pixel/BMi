"""Game Arena uchun ma'lumotlar bilan to'ldirish skripti"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lms_project.settings')
django.setup()

from courses.models import TypingText, CodeChallenge, MemoryCard

# Avvalgilarni tozalash
TypingText.objects.all().delete()
CodeChallenge.objects.all().delete()
MemoryCard.objects.all().delete()

# ============ TYPING TEXTS ============

# EASY (5 ta)
easy_texts = [
    "Python dasturlash tili bugungi kunda eng mashhur tillardan biri hisoblanadi. U sodda sintaksisi va kuchli kutubxonalari bilan ajralib turadi.",
    "Dasturlashni o'rganish sabr va amaliyot talab qiladi. Har kuni kod yozish malakangizni oshiradi va yangi imkoniyatlar eshigini ochadi.",
    "Kompyuter fanlari zamonaviy dunyoning asosiy yo'nalishlaridan biridir. Algoritmlar va ma'lumotlar tuzilmasi dasturlashning poydevori hisoblanadi.",
    "Sun'iy intellekt texnologiyalari hayotimizning barcha sohalariga kirib kelmoqda. Mashinali o'rganish va neyron tarmoqlar buning asosiy vositalaridir.",
    "Veb dasturlash frontend va backend qismlardan iborat. HTML sahifa tuzilmasini, CSS dizaynni, JavaScript esa interaktivlikni ta'minlaydi.",
]
for t in easy_texts:
    TypingText.objects.create(text=t, difficulty='easy', language='uz')

# MEDIUM (5 ta)
medium_texts = [
    "Django framework Python tilida yozilgan kuchli veb framework hisoblanadi. U MVC arxitekturasiga asoslangan bo'lib, tez va xavfsiz veb ilovalar yaratishga yordam beradi. Django ORM tizimi ma'lumotlar bazasi bilan ishlashni osonlashtiradi va SQL so'rovlarini avtomatik generatsiya qiladi.",
    "Git versiyalarni boshqarish tizimi dasturchilar uchun eng muhim vositalardan biridir. U kodning har bir o'zgarishini kuzatib boradi va jamoaviy ishlashni osonlashtiradi. Branch va merge tushunchalari parallel ravishda ishlash imkonini beradi.",
    "API yaratish zamonaviy dasturlashning ajralmas qismidir. REST arxitekturasi HTTP metodlari orqali ma'lumotlarni almashish imkonini beradi. JSON formati eng keng tarqalgan ma'lumot almashish formati hisoblanadi va deyarli barcha dasturlash tillari tomonidan qo'llab-quvvatlanadi.",
    "Ma'lumotlar bazasi har qanday dasturning asosiy qismi hisoblanadi. SQL tili relyatsion bazalar bilan ishlash uchun standart til bo'lib, SELECT, INSERT, UPDATE va DELETE buyruqlari orqali ma'lumotlarni boshqarish mumkin. Indekslar so'rovlar tezligini sezilarli oshiradi.",
    "Linux operatsion tizimi serverlar dunyosida eng ko'p ishlatiladigan tizimdir. Terminal orqali fayllar bilan ishlash, dasturlarni o'rnatish va tizimni boshqarish mumkin. Bash skriptlari takroriy vazifalarni avtomatlashtirish uchun ishlatiladi va DevOps sohasida keng qo'llaniladi.",
]
for t in medium_texts:
    TypingText.objects.create(text=t, difficulty='medium', language='uz')

# HARD (5 ta)
hard_texts = [
    "Mikroservislar arxitekturasi yirik dasturiy ta'minotni mustaqil xizmatlarga bo'lish yondashuvidir. Har bir mikroservis o'z ma'lumotlar bazasiga ega bo'lib, API orqali boshqa xizmatlar bilan aloqa qiladi. Docker konteynerlari va Kubernetes orkestrasiya tizimi mikroservislarni joylashtirish va boshqarishni osonlashtiradi. Bu arxitektura kengayuvchanlik va mustaqil deploy qilish imkonini beradi.",
    "Kriptografiya axborot xavfsizligining asosiy yo'nalishi bo'lib, ma'lumotlarni shifrlash va deshifrlash usullarini o'rganadi. Simmetrik shifrlashda bitta kalit ishlatiladi, assimetrik shifrlashda esa ochiq va yopiq kalitlar juftligi qo'llaniladi. SHA-256 va AES zamonaviy kriptografik algoritmlarning eng keng tarqalganlari hisoblanadi.",
    "Machine Learning modellarini yaratish uchun ma'lumotlarni yig'ish, tozalash va tayyorlash jarayoni juda muhimdir. Supervised learning usulida model belgilangan ma'lumotlar asosida o'rgatiladi. Neural network arxitekturasi tabaqalar va og'irliklardan iborat bo'lib, backpropagation algoritmi orqali o'rgatiladi. TensorFlow va PyTorch kutubxonalari bu sohada eng mashhur vositalardir.",
    "DevOps madaniyati dasturlash va operatsiyalar jamoalarini birlashtirib, dasturiy ta'minotni tezroq va sifatliroq yetkazib berishni maqsad qiladi. CI/CD pipeline orqali kod avtomatik test qilinadi va deploy qilinadi. Infrastructure as Code yondashuvi server konfiguratsiyasini kod sifatida saqlash imkonini beradi. Monitoring va logging tizimlar dastur holatini real vaqtda kuzatib boradi.",
    "Blockchain texnologiyasi markazlashmagan va o'zgartirib bo'lmaydigan ma'lumotlar tizimini yaratadi. Har bir blok oldingi blokning xesh qiymatini o'z ichiga oladi va bu zanjir yaxlitligini ta'minlaydi. Konsensus mexanizmlari tarmoq ishtirokchilari o'rtasida kelishuvga erishish uchun ishlatiladi. Smart kontraktlar dasturlashtiriladigan shartlarni avtomatik bajarilishini ta'minlaydi.",
]
for t in hard_texts:
    TypingText.objects.create(text=t, difficulty='hard', language='uz')

print(f"TypingText: {TypingText.objects.count()} ta yaratildi")

# ============ CODE CHALLENGES ============

# EASY (5 ta)
CodeChallenge.objects.create(
    title="Juft yoki toq",
    description="Berilgan sonning juft yoki toqligini aniqlang.\n\nKiritilgan son juft bo'lsa \"Juft\", toq bo'lsa \"Toq\" deb chiqaring.",
    difficulty='easy',
    initial_code="n = int(input())\n# Yechimingizni yozing\n",
    solution='n = int(input())\nif n % 2 == 0:\n    print("Juft")\nelse:\n    print("Toq")',
    test_cases=[
        {"input": "4", "expected": "Juft"},
        {"input": "7", "expected": "Toq"},
        {"input": "0", "expected": "Juft"},
        {"input": "13", "expected": "Toq"},
    ],
    time_limit=120, xp_reward=20
)

CodeChallenge.objects.create(
    title="Eng katta son",
    description="Uchta son kiritiladi. Ularning eng kattasini toping va chiqaring.",
    difficulty='easy',
    initial_code="a = int(input())\nb = int(input())\nc = int(input())\n# Eng katta sonni toping\n",
    solution='a = int(input())\nb = int(input())\nc = int(input())\nprint(max(a, b, c))',
    test_cases=[
        {"input": "3\n7\n5", "expected": "7"},
        {"input": "10\n2\n8", "expected": "10"},
        {"input": "1\n1\n1", "expected": "1"},
        {"input": "-5\n-2\n-8", "expected": "-2"},
    ],
    time_limit=120, xp_reward=20
)

CodeChallenge.objects.create(
    title="Faktorial hisoblash",
    description="Berilgan n sonning faktorialini hisoblang.\n\nn! = 1 * 2 * 3 * ... * n\n0! = 1",
    difficulty='easy',
    initial_code="n = int(input())\n# n! ni hisoblang\n",
    solution='n = int(input())\nresult = 1\nfor i in range(1, n+1):\n    result *= i\nprint(result)',
    test_cases=[
        {"input": "5", "expected": "120"},
        {"input": "0", "expected": "1"},
        {"input": "1", "expected": "1"},
        {"input": "7", "expected": "5040"},
    ],
    time_limit=120, xp_reward=20
)

CodeChallenge.objects.create(
    title="Sonlar yig'indisi",
    description="1 dan n gacha bo'lgan sonlar yig'indisini hisoblang.",
    difficulty='easy',
    initial_code="n = int(input())\n# 1 dan n gacha yig'indini hisoblang\n",
    solution='n = int(input())\nprint(n * (n + 1) // 2)',
    test_cases=[
        {"input": "5", "expected": "15"},
        {"input": "10", "expected": "55"},
        {"input": "1", "expected": "1"},
        {"input": "100", "expected": "5050"},
    ],
    time_limit=120, xp_reward=20
)

CodeChallenge.objects.create(
    title="Teskari string",
    description='Berilgan matnni teskari tartibda chiqaring.\n\nMasalan: "salom" -> "molas"',
    difficulty='easy',
    initial_code="s = input()\n# Teskari qiling\n",
    solution='s = input()\nprint(s[::-1])',
    test_cases=[
        {"input": "salom", "expected": "molas"},
        {"input": "python", "expected": "nohtyp"},
        {"input": "abcde", "expected": "edcba"},
        {"input": "a", "expected": "a"},
    ],
    time_limit=120, xp_reward=20
)

# MEDIUM (5 ta)
CodeChallenge.objects.create(
    title="Tub son tekshirish",
    description='Berilgan son tub son ekanligini aniqlang.\n\nTub son faqat 1 ga va o\'ziga bo\'linadi.\n\nTub bo\'lsa "Ha", aks holda "Yo\'q" deb chiqaring.',
    difficulty='medium',
    initial_code="n = int(input())\n# Tub son ekanligini tekshiring\n",
    solution='n = int(input())\nif n < 2:\n    print("Yo\'q")\nelse:\n    is_prime = True\n    for i in range(2, int(n**0.5) + 1):\n        if n % i == 0:\n            is_prime = False\n            break\n    print("Ha" if is_prime else "Yo\'q")',
    test_cases=[
        {"input": "7", "expected": "Ha"},
        {"input": "12", "expected": "Yo'q"},
        {"input": "2", "expected": "Ha"},
        {"input": "1", "expected": "Yo'q"},
        {"input": "29", "expected": "Ha"},
    ],
    time_limit=180, xp_reward=35
)

CodeChallenge.objects.create(
    title="Fibonacci ketma-ketligi",
    description="n-chi Fibonacci sonini toping.\n\nFibonacci: 0, 1, 1, 2, 3, 5, 8, 13, 21, ...\n\nF(0) = 0, F(1) = 1, F(n) = F(n-1) + F(n-2)",
    difficulty='medium',
    initial_code="n = int(input())\n# n-chi Fibonacci sonini toping\n",
    solution='n = int(input())\na, b = 0, 1\nfor _ in range(n):\n    a, b = b, a + b\nprint(a)',
    test_cases=[
        {"input": "0", "expected": "0"},
        {"input": "1", "expected": "1"},
        {"input": "6", "expected": "8"},
        {"input": "10", "expected": "55"},
    ],
    time_limit=180, xp_reward=35
)

CodeChallenge.objects.create(
    title="Palindrom tekshirish",
    description='Berilgan matn palindrom ekanligini aniqlang.\n\nPalindrom - oldidan va orqasidan bir xil o\'qiladigan so\'z.\n\nPalindrom bo\'lsa "Ha", aks holda "Yo\'q" chiqaring.',
    difficulty='medium',
    initial_code="s = input().lower()\n# Palindrom ekanligini tekshiring\n",
    solution='s = input().lower()\nprint("Ha" if s == s[::-1] else "Yo\'q")',
    test_cases=[
        {"input": "aba", "expected": "Ha"},
        {"input": "salom", "expected": "Yo'q"},
        {"input": "abacaba", "expected": "Ha"},
        {"input": "racecar", "expected": "Ha"},
    ],
    time_limit=180, xp_reward=35
)

CodeChallenge.objects.create(
    title="Raqamlar yig'indisi",
    description="Berilgan sonning raqamlari yig'indisini hisoblang.\n\nMasalan: 123 -> 1+2+3 = 6",
    difficulty='medium',
    initial_code="n = int(input())\n# Raqamlar yig'indisini hisoblang\n",
    solution='n = int(input())\nprint(sum(int(d) for d in str(abs(n))))',
    test_cases=[
        {"input": "123", "expected": "6"},
        {"input": "9999", "expected": "36"},
        {"input": "0", "expected": "0"},
        {"input": "507", "expected": "12"},
    ],
    time_limit=180, xp_reward=35
)

CodeChallenge.objects.create(
    title="So'zlarni sanash",
    description="Berilgan matndagi so'zlar sonini hisoblang.",
    difficulty='medium',
    initial_code="s = input()\n# So'zlar sonini hisoblang\n",
    solution='s = input()\nprint(len(s.split()))',
    test_cases=[
        {"input": "salom dunyo", "expected": "2"},
        {"input": "python dasturlash tili", "expected": "3"},
        {"input": "test", "expected": "1"},
        {"input": "bu yerda beshta soz bor", "expected": "5"},
    ],
    time_limit=180, xp_reward=35
)

# HARD (5 ta)
CodeChallenge.objects.create(
    title="Bubble Sort",
    description="Berilgan sonlar ro'yxatini Bubble Sort algoritmi yordamida kichikdan kattaga tartiblang.\n\nBirinchi qatorda n - elementlar soni.\nIkkinchi qatorda n ta son bo'sh joy bilan ajratilgan.\n\nTartiblangan ro'yxatni chiqaring.",
    difficulty='hard',
    initial_code="n = int(input())\narr = list(map(int, input().split()))\n# Bubble sort yozing\n",
    solution='n = int(input())\narr = list(map(int, input().split()))\nfor i in range(n):\n    for j in range(0, n-i-1):\n        if arr[j] > arr[j+1]:\n            arr[j], arr[j+1] = arr[j+1], arr[j]\nprint(*arr)',
    test_cases=[
        {"input": "5\n5 3 8 1 2", "expected": "1 2 3 5 8"},
        {"input": "4\n4 3 2 1", "expected": "1 2 3 4"},
        {"input": "3\n1 2 3", "expected": "1 2 3"},
        {"input": "6\n9 1 5 3 7 2", "expected": "1 2 3 5 7 9"},
    ],
    time_limit=300, xp_reward=50
)

CodeChallenge.objects.create(
    title="Binary Search",
    description="Tartiblangan ro'yxatda berilgan sonni Binary Search algoritmi bilan toping.\n\nBirinchi qator: n - elementlar soni\nIkkinchi qator: n ta tartiblangan son\nUchinchi qator: qidirilayotgan son\n\nTopilsa indeksini (0 dan boshlab), topilmasa -1 chiqaring.",
    difficulty='hard',
    initial_code="n = int(input())\narr = list(map(int, input().split()))\ntarget = int(input())\n# Binary search yozing\n",
    solution='n = int(input())\narr = list(map(int, input().split()))\ntarget = int(input())\nleft, right = 0, n - 1\nresult = -1\nwhile left <= right:\n    mid = (left + right) // 2\n    if arr[mid] == target:\n        result = mid\n        break\n    elif arr[mid] < target:\n        left = mid + 1\n    else:\n        right = mid - 1\nprint(result)',
    test_cases=[
        {"input": "5\n1 3 5 7 9\n5", "expected": "2"},
        {"input": "5\n1 3 5 7 9\n4", "expected": "-1"},
        {"input": "6\n2 4 6 8 10 12\n12", "expected": "5"},
        {"input": "3\n1 2 3\n1", "expected": "0"},
    ],
    time_limit=300, xp_reward=50
)

CodeChallenge.objects.create(
    title="FizzBuzz",
    description='1 dan n gacha sonlarni chiqaring.\n3 ga bo\'linadiganlar uchun "Fizz"\n5 ga bo\'linadiganlar uchun "Buzz"\n3 va 5 ga bo\'linadiganlar uchun "FizzBuzz"\nQolganlar uchun sonning o\'zini chiqaring.\n\nHar bir natijani yangi qatorda chiqaring.',
    difficulty='hard',
    initial_code="n = int(input())\n# FizzBuzz yozing\n",
    solution='n = int(input())\nfor i in range(1, n+1):\n    if i % 15 == 0:\n        print("FizzBuzz")\n    elif i % 3 == 0:\n        print("Fizz")\n    elif i % 5 == 0:\n        print("Buzz")\n    else:\n        print(i)',
    test_cases=[
        {"input": "5", "expected": "1\n2\nFizz\n4\nBuzz"},
        {"input": "15", "expected": "1\n2\nFizz\n4\nBuzz\nFizz\n7\n8\nFizz\nBuzz\n11\nFizz\n13\n14\nFizzBuzz"},
        {"input": "3", "expected": "1\n2\nFizz"},
    ],
    time_limit=300, xp_reward=50
)

CodeChallenge.objects.create(
    title="Matritsa transpozitsiyasi",
    description="Berilgan n*m matritsaning transpozitsiyasini toping.\n\nBirinchi qator: n va m (qatorlar va ustunlar soni)\nKeyingi n qator: matritsaning har bir qatori\n\nTranspozitsiya qilingan matritsani chiqaring.",
    difficulty='hard',
    initial_code="n, m = map(int, input().split())\nmatrix = []\nfor i in range(n):\n    row = list(map(int, input().split()))\n    matrix.append(row)\n# Transpozitsiyani hisoblang\n",
    solution='n, m = map(int, input().split())\nmatrix = []\nfor i in range(n):\n    row = list(map(int, input().split()))\n    matrix.append(row)\nfor j in range(m):\n    print(*[matrix[i][j] for i in range(n)])',
    test_cases=[
        {"input": "2 3\n1 2 3\n4 5 6", "expected": "1 4\n2 5\n3 6"},
        {"input": "3 3\n1 0 0\n0 1 0\n0 0 1", "expected": "1 0 0\n0 1 0\n0 0 1"},
        {"input": "1 4\n1 2 3 4", "expected": "1\n2\n3\n4"},
    ],
    time_limit=300, xp_reward=50
)

CodeChallenge.objects.create(
    title="Anagram tekshirish",
    description='Ikkita so\'z anagram ekanligini aniqlang.\n\nAnagram - bir xil harflardan tuzilgan, lekin tartib boshqacha so\'zlar.\n\nBirinchi qator: birinchi so\'z\nIkkinchi qator: ikkinchi so\'z\n\nAnagram bo\'lsa "Ha", aks holda "Yo\'q" chiqaring.',
    difficulty='hard',
    initial_code="s1 = input().lower()\ns2 = input().lower()\n# Anagram ekanligini tekshiring\n",
    solution='s1 = input().lower()\ns2 = input().lower()\nprint("Ha" if sorted(s1) == sorted(s2) else "Yo\'q")',
    test_cases=[
        {"input": "listen\nsilent", "expected": "Ha"},
        {"input": "hello\nworld", "expected": "Yo'q"},
        {"input": "triangle\nintegral", "expected": "Ha"},
        {"input": "abc\nabcd", "expected": "Yo'q"},
    ],
    time_limit=300, xp_reward=50
)

print(f"CodeChallenge: {CodeChallenge.objects.count()} ta yaratildi")

# ============ MEMORY CARDS ============

memory_data = [
    # Dasturlash asoslari
    ("Variable", "Ma'lumot saqlash joyi", "programming"),
    ("Function", "Qayta ishlatiladigan kod bloki", "programming"),
    ("Loop", "Kodni takroriy bajarish", "programming"),
    ("Array", "Tartiblangan elementlar ro'yxati", "programming"),
    ("If/Else", "Shartli bajarish operatori", "programming"),
    ("Class", "Obyekt yaratish shabloni", "programming"),
    ("String", "Matnli ma'lumot turi", "programming"),
    ("Boolean", "True yoki False qiymat", "programming"),
    ("Algorithm", "Masalani yechish qadamlari", "programming"),
    ("Recursion", "Funksiya o'zini chaqirishi", "programming"),
    ("Stack", "LIFO tartibli ma'lumot tuzilmasi", "programming"),
    ("Queue", "FIFO tartibli ma'lumot tuzilmasi", "programming"),

    # Python
    ("def", "Funksiya e'lon qilish", "python"),
    ("list", "O'zgaruvchan ketma-ketlik", "python"),
    ("dict", "Kalit-qiymat juftliklari", "python"),
    ("tuple", "O'zgarmas ketma-ketlik", "python"),
    ("lambda", "Anonim funksiya", "python"),
    ("pip", "Paket menejeri", "python"),
    ("self", "Joriy obyektga havola", "python"),
    ("__init__", "Konstruktor metodi", "python"),
    ("try/except", "Xatolarni ushlash", "python"),
    ("import", "Modulni ulash", "python"),
    ("range()", "Sonlar ketma-ketligi", "python"),
    ("len()", "Uzunlikni hisoblash", "python"),

    # Veb
    ("HTML", "Sahifa tuzilmasi tili", "web"),
    ("CSS", "Sahifa dizayni tili", "web"),
    ("JavaScript", "Sahifa interaktivligi", "web"),
    ("API", "Dasturlar aloqa interfeysi", "web"),
    ("HTTP", "Veb aloqa protokoli", "web"),
    ("DOM", "Sahifa obyektlar modeli", "web"),
    ("JSON", "Ma'lumot almashish formati", "web"),
    ("REST", "API arxitektura uslubi", "web"),
    ("Cookie", "Brauzerda saqlangan ma'lumot", "web"),
    ("URL", "Veb manzil", "web"),

    # Database
    ("SQL", "Ma'lumotlar bazasi so'rov tili", "database"),
    ("SELECT", "Ma'lumotlarni o'qish", "database"),
    ("INSERT", "Yangi yozuv qo'shish", "database"),
    ("PRIMARY KEY", "Yagona identifikator", "database"),
    ("FOREIGN KEY", "Jadvallar bog'lovchisi", "database"),
    ("INDEX", "Qidiruv tezlashtiruvchi", "database"),
    ("JOIN", "Jadvallarni birlashtirish", "database"),
    ("ORM", "Obyekt-relyatsion xaritalash", "database"),

    # Umumiy IT
    ("Git", "Versiyalarni boshqarish tizimi", "general"),
    ("Linux", "Ochiq kodli operatsion tizim", "general"),
    ("Docker", "Konteynerlashtirish platformasi", "general"),
    ("CI/CD", "Uzluksiz integratsiya va yetkazish", "general"),
    ("Cloud", "Masofaviy hisoblash xizmati", "general"),
    ("SSH", "Xavfsiz masofaviy ulanish", "general"),
    ("Terminal", "Buyruq qatori interfeysi", "general"),
    ("Debug", "Xatolarni topish va tuzatish", "general"),
    ("Framework", "Dasturlash uchun tayyor asos", "general"),
    ("IDE", "Dasturlash muhiti", "general"),
]

for term, match, category in memory_data:
    MemoryCard.objects.create(term=term, match=match, category=category)

print(f"MemoryCard: {MemoryCard.objects.count()} ta yaratildi")
print("\nBarcha ma'lumotlar muvaffaqiyatli qo'shildi!")
