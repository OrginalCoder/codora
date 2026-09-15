from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from apps.marketplace.models import Category


class Command(BaseCommand):
    help = "Codora marketpleysi uchun asosiy kategoriyalar va superuser yaratish"

    def handle(self, *args, **kwargs):
        self.stdout.write("Boshlang‘ich ma’lumotlar tekshirilmoqda...")

        admin_user, created = User.objects.get_or_create(username='admin', defaults={
            'email': 'admin@codora.uz',
            'is_staff': True,
            'is_superuser': True,
            'first_name': 'Admin'
        })
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write(self.style.SUCCESS("Superuser 'admin' (parol: admin123) muvaffaqiyatli yaratildi."))

        categories_data = [
            {'name': 'Telegram Botlar', 'icon': '🤖', 'order': 1, 'is_featured': True,
             'description': 'Telegram platformasi uchun ko‘p funksiyali, sun’iy intellekt va to‘lov tizimlariga ulangan professional botlar.'},
            {'name': 'Manba Kodlari', 'icon': '💻', 'order': 2, 'is_featured': True,
             'description': 'Django, FastAPI, Node.js va boshqa platformalarda yozilgan tayyor biznes dasturlar manba kodlari.'},
            {'name': 'Veb-sayt Shablonlari', 'icon': '🌐', 'order': 3, 'is_featured': True,
             'description': 'Zamonaviy internet-do‘konlar, lendinglar va portfolio sahifalari uchun HTML/CSS shablonlar.'},
            {'name': 'Mobil Ilovalar', 'icon': '📱', 'order': 4, 'is_featured': True,
             'description': 'Flutter va React Native uchun to‘liq tayyor kross-platforma mobil ilova shablonlari.'},
            {'name': 'UI Kitlar', 'icon': '🎨', 'order': 5, 'is_featured': True,
             'description': 'Figma va zamonaviy veb-loyihalar uchun premium dizayn tizimlari va komponentlar to‘plami.'},
            {'name': 'APIs', 'icon': '🔌', 'order': 6, 'is_featured': True,
             'description': 'Turli xizmatlar, to‘lovlar va ma’lumotlar bilan ishlash uchun tayyor RESTful API yechimlari.'},
            {'name': 'Plaginlar', 'icon': '🧩', 'order': 7, 'is_featured': False,
             'description': 'Turli CMS tizimlari va freymvorklar uchun qo‘shimcha imkoniyatlarni kengaytiruvchi modullar.'},
            {'name': 'Skriptlar', 'icon': '📦', 'order': 8, 'is_featured': False,
             'description': 'Avtomatlashtirish, parsing va ma’lumotlarni tahlil qilish uchun yengil va tezkor skriptlar.'},
            {'name': 'Grafika', 'icon': '🖼️', 'order': 9, 'is_featured': False,
             'description': 'Ikonkalar, vektor illyustratsiyalar, bannerlar va brending to‘plamlari.'},
            {'name': 'Elektron Kitoblar', 'icon': '📚', 'order': 10, 'is_featured': False,
             'description': 'Dasturlash, IT arxitekturasi va dizayn bo‘yicha professional qo‘llanmalar.'},
            {'name': 'Kurslar', 'icon': '🎓', 'order': 11, 'is_featured': False,
             'description': 'Amaliyotga yo‘naltirilgan video darsliklar va o‘quv dasturlari.'},
        ]

        for c in categories_data:
            Category.objects.get_or_create(name=c['name'], defaults={
                'icon': c['icon'],
                'order': c['order'],
                'is_featured': c['is_featured'],
                'description': c['description'],
            })

        self.stdout.write(self.style.SUCCESS("Barcha kategoriyalar muvaffaqiyatli saqlandi."))
        self.stdout.write(self.style.SUCCESS("Baza toza holatda: ortiqcha mahsulot va sotuvchilar qo‘shilmadi."))
