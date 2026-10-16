from html import escape

from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db.models import ForeignKey, ManyToManyField, OneToOneField
from django.templatetags.static import static

_KIND = {
    OneToOneField: "یک‌به‌یک",
    ForeignKey: "چندبه‌یک",
    ManyToManyField: "چندبه‌چند",
}


def render_erd():
    models = _models()
    links = _links(models)
    font = escape(static("css/fonts.css"))
    return _PAGE.format(
        font=font,
        diagram=escape(_diagram(links), quote=False),
        cards="".join(_card(model) for model in models),
        rows="".join(_row(link) for link in links),
    )


def _models():
    user = get_user_model()
    own = sorted(apps.get_app_config("honaryaar").get_models(), key=lambda model: model.__name__)
    return [user, *own]


def _links(models):
    links = []
    for model in models:
        if model._meta.app_label != "honaryaar":
            continue
        for field in model._meta.local_fields:
            if not isinstance(field, (ForeignKey, OneToOneField)):
                continue
            if field.related_model is ContentType:
                continue
            links.append(_relation(model, field))
        for field in model._meta.local_many_to_many:
            if not field.remote_field.through._meta.auto_created:
                continue
            links.append(_relation(model, field))
        for field in model._meta.private_fields:
            if isinstance(field, GenericForeignKey):
                links.append(
                    {
                        "source": model.__name__,
                        "field": field.name,
                        "target": "هدف عمومی",
                        "kind": "کلید عمومی",
                        "delete": "—",
                        "required": "خیر",
                        "diagram": False,
                    }
                )
    return links


def _relation(model, field):
    if isinstance(field, ManyToManyField):
        cardinality = "}o--o{"
        delete = "CASCADE"
        required = "خیر" if field.blank else "بله"
        left = model.__name__
        right = field.related_model.__name__
    elif isinstance(field, OneToOneField):
        cardinality = "|o--o|" if field.null else "||--o|"
        delete = field.remote_field.on_delete.__name__.replace("_", " ").upper()
        required = "خیر" if field.null else "بله"
        left = field.related_model.__name__
        right = model.__name__
    else:
        cardinality = "|o--o{" if field.null else "||--o{"
        delete = field.remote_field.on_delete.__name__.replace("_", " ").upper()
        required = "خیر" if field.null else "بله"
        left = field.related_model.__name__
        right = model.__name__
    return {
        "source": model.__name__,
        "field": field.name,
        "target": field.related_model.__name__,
        "kind": _KIND[type(field)],
        "delete": delete,
        "required": required,
        "diagram": True,
        "left": left,
        "right": right,
        "cardinality": cardinality,
    }


def _diagram(links):
    lines = ["erDiagram"]
    for link in links:
        if not link["diagram"]:
            continue
        lines.append(f'    {link["left"]} {link["cardinality"]} {link["right"]} : "{link["field"]}"')
    return "\n".join(lines)


def _card(model):
    subtitle = escape(str(model._meta.verbose_name))
    if model._meta.app_label != "honaryaar":
        subtitle = "کاربر جنگو"
    items = []
    for field in list(model._meta.local_fields) + list(model._meta.local_many_to_many):
        if field.name == "password" or getattr(field, "primary_key", False):
            continue
        if getattr(field, "related_model", None) is ContentType:
            continue
        items.append(f"<li>{_field_line(field)}</li>")
    for field in model._meta.private_fields:
        if isinstance(field, GenericForeignKey):
            items.append(f"<li><code>{escape(field.name)}</code> کلید عمومی</li>")
    body = "".join(items)
    return (
        '<article class="ent">'
        f"<header><h3>{escape(model.__name__)}</h3><span>{subtitle}</span></header>"
        f"<ul>{body}</ul>"
        "</article>"
    )


def _field_line(field):
    name = escape(field.name)
    if isinstance(field, (ForeignKey, OneToOneField, ManyToManyField)):
        target = escape(field.related_model.__name__)
        kind = _KIND[type(field)]
        optional = "، اختیاری" if _optional(field) else ""
        return f"<code>{name}</code> → {target}، {kind}{optional}"
    note = ""
    choices = getattr(field, "choices", None) or []
    values = [str(value) for value, _label in choices if value not in (None, "")]
    if values:
        shown = "، ".join(escape(value) for value in values[:12])
        if len(values) > 12:
            shown += "، …"
        note = f" فهرست: {shown}"
    elif _optional(field):
        note = "، اختیاری"
    return f"<code>{name}</code>{note}"


def _optional(field):
    if getattr(field, "primary_key", False):
        return False
    if getattr(field, "auto_now", False) or getattr(field, "auto_now_add", False):
        return False
    return bool(getattr(field, "null", False) or getattr(field, "blank", False))


def _row(link):
    cells = [
        f'{link["source"]}.{link["field"]}',
        link["target"],
        link["kind"],
        link["delete"],
        link["required"],
    ]
    return "<tr>" + "".join(f"<td>{escape(cell)}</td>" for cell in cells) + "</tr>"


_PAGE = """<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>هنریار · رابطهٔ مدل‌ها</title>
  <link rel="stylesheet" href="{font}">
  <style>
    :root {{
      --ink: #17131a;
      --muted: #5c564f;
      --line: #e6e1da;
      --paper: #f6f4ef;
      --card: #fff;
      --brand: #c13281;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--paper);
      color: var(--ink);
      font-family: Vazirmatn, Tahoma, sans-serif;
      font-size: 14px;
      line-height: 1.7;
    }}
    main {{ width: min(1080px, calc(100% - 32px)); margin: 28px auto 64px; }}
    h1 {{ margin: 0 0 8px; font-size: 28px; line-height: 1.35; }}
    h2 {{ margin: 36px 0 10px; font-size: 20px; }}
    h3 {{ margin: 0; font-size: 16px; }}
    p {{ margin: 0 0 10px; }}
    code {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.92em; }}
    .lead {{ color: var(--muted); max-width: 46rem; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 12px; }}
    .ent {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 14px 16px;
    }}
    .ent header {{ display: flex; justify-content: space-between; gap: 8px; align-items: baseline; }}
    .ent header span {{ color: var(--muted); font-size: 12px; }}
    ul {{ margin: 8px 0 0; padding: 0 18px 0 0; }}
    li {{ margin: 2px 0; }}
    table {{ width: 100%; border-collapse: collapse; background: var(--card); border-radius: 16px; overflow: hidden; }}
    th, td {{ text-align: right; padding: 8px 10px; border-bottom: 1px solid var(--line); vertical-align: top; }}
    th {{ font-size: 12px; color: var(--muted); font-weight: 700; }}
    .mermaid {{ background: var(--card); border: 1px solid var(--line); border-radius: 16px; padding: 12px; overflow: auto; }}
  </style>
</head>
<body>
<main>
  <p class="lead">از مدل‌های فعلی ساخته می‌شود. با هر تغییر مدل، همین صفحه به‌روز است.</p>
  <h1>رابطهٔ مدل‌های هنریار</h1>
  <h2>نمودار</h2>
  <div class="mermaid">
{diagram}
  </div>
  <h2>مدل‌ها</h2>
  <div class="grid">
    {cards}
  </div>
  <h2>رابطه‌ها</h2>
  <table>
    <thead>
      <tr><th>از</th><th>به</th><th>نوع</th><th>حذف</th><th>اجباری</th></tr>
    </thead>
    <tbody>
      {rows}
    </tbody>
  </table>
</main>
<script type="module">
  import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
  mermaid.initialize({{ startOnLoad: true, theme: "neutral", er: {{ useMaxWidth: true }} }});
</script>
</body>
</html>
"""
