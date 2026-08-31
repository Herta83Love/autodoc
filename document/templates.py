PAGE_TEMPLATE = """
# {{ title }}

網址

{{ url }}

## 畫面截圖

{{ screenshot }}

## 欄位

{% for field in fields %}
- {{ field }}
{% endfor %}

## 按鈕

{% for button in buttons %}
- {{ button }}
{% endfor %}

"""