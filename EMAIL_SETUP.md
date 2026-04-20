# Gmail SMTP Setup

Parol tiklash kodi foydalanuvchi ro'yxatdan o'tishda kiritgan email manziliga yuboriladi.

## Local development

Hech qanday SMTP env berilmasa, email xabarlar console/log ichida ko'rinadi.

## Gmail SMTP env

`.env` yoki deploy env ichiga quyidagilarni kiriting:

```env
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=true
EMAIL_HOST_USER=yourgmail@gmail.com
EMAIL_HOST_PASSWORD=your-google-app-password
DEFAULT_FROM_EMAIL=LMS Platform <yourgmail@gmail.com>
SERVER_EMAIL=yourgmail@gmail.com
```

## Muhim

- Oddiy Gmail paroli emas, `Google App Password` ishlatilishi kerak.
- Gmail akkauntda `2-Step Verification` yoqilgan bo'lishi kerak.
- `EMAIL_HOST_USER` va `EMAIL_HOST_PASSWORD` berilsa, tizim avtomatik SMTP backendga o'tadi.
- Bu qiymatlar berilmasa, tizim emailni console backend orqali chiqaradi.
