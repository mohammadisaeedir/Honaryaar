from django.db import migrations, models


PERSIAN_TO_SLUG = {
    "آذربایجان شرقی": "east-azerbaijan",
    "آذربایجان غربی": "west-azerbaijan",
    "اردبیل": "ardabil",
    "اصفهان": "isfahan",
    "البرز": "alborz",
    "ایلام": "ilam",
    "بوشهر": "bushehr",
    "تهران": "tehran",
    "چهارمحال و بختیاری": "chaharmahal-bakhtiari",
    "خراسان جنوبی": "south-khorasan",
    "خراسان رضوی": "razavi-khorasan",
    "خراسان شمالی": "north-khorasan",
    "خوزستان": "khuzestan",
    "زنجان": "zanjan",
    "سمنان": "semnan",
    "سیستان و بلوچستان": "sistan-baluchestan",
    "فارس": "fars",
    "قزوین": "qazvin",
    "قم": "qom",
    "کردستان": "kurdistan",
    "کرمان": "kerman",
    "کرمانشاه": "kermanshah",
    "کهگیلویه و بویراحمد": "kohgiluyeh-boyer-ahmad",
    "گلستان": "golestan",
    "گیلان": "gilan",
    "لرستان": "lorestan",
    "مازندران": "mazandaran",
    "مرکزی": "markazi",
    "هرمزگان": "hormozgan",
    "همدان": "hamadan",
    "یزد": "yazd",
}


def provinces_to_slugs(apps, schema_editor):
    City = apps.get_model("honaryaar", "City")
    for city in City.objects.all():
        slug = PERSIAN_TO_SLUG.get(city.province)
        if slug and slug != city.province:
            city.province = slug
            city.save(update_fields=["province"])


class Migration(migrations.Migration):
    dependencies = [
        ("honaryaar", "0021_artcategory_art"),
    ]

    operations = [
        migrations.RunPython(provinces_to_slugs, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="city",
            name="province",
            field=models.CharField(
                blank=True,
                choices=[
                    ("alborz", "Alborz"),
                    ("ardabil", "Ardabil"),
                    ("bushehr", "Bushehr"),
                    ("chaharmahal-bakhtiari", "Chaharmahal and Bakhtiari"),
                    ("east-azerbaijan", "East Azerbaijan"),
                    ("fars", "Fars"),
                    ("gilan", "Gilan"),
                    ("golestan", "Golestan"),
                    ("hamadan", "Hamadan"),
                    ("hormozgan", "Hormozgan"),
                    ("ilam", "Ilam"),
                    ("isfahan", "Isfahan"),
                    ("kerman", "Kerman"),
                    ("kermanshah", "Kermanshah"),
                    ("khuzestan", "Khuzestan"),
                    ("kohgiluyeh-boyer-ahmad", "Kohgiluyeh and Boyer-Ahmad"),
                    ("kurdistan", "Kurdistan"),
                    ("lorestan", "Lorestan"),
                    ("markazi", "Markazi"),
                    ("mazandaran", "Mazandaran"),
                    ("north-khorasan", "North Khorasan"),
                    ("qazvin", "Qazvin"),
                    ("qom", "Qom"),
                    ("razavi-khorasan", "Razavi Khorasan"),
                    ("semnan", "Semnan"),
                    ("sistan-baluchestan", "Sistan and Baluchestan"),
                    ("south-khorasan", "South Khorasan"),
                    ("tehran", "Tehran"),
                    ("west-azerbaijan", "West Azerbaijan"),
                    ("yazd", "Yazd"),
                    ("zanjan", "Zanjan"),
                ],
                max_length=40,
            ),
        ),
    ]
