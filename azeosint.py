import asyncio
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties
from datetime import datetime, timedelta

# ==================================================
#   ANA BOT TOKEN – BUNU DƏYİŞ QARDAŞ
# ==================================================
BOT_TOKEN = "8033740858:AAHrbEqkQnuiBY3O_lwp1pDDVBTWuMgXSl0"

BASE_LIMIT = 15
users = {}

# API'ler
AZERCELL_API = "https://apimy.az/api/azercell?number="
KAHIN_API = "https://kahin.org/api/check-number?number="
ZAPCALLER_API = "https://api.zapcaller.com/lookup?number="
NUMVERIFY_KEY = "7c7a4429a93351ffbcb6155efae5cb96"
NUMVERIFY_API = f"http://apilayer.net/api/validate?access_key={NUMVERIFY_KEY}&number="

# Truecaller üçün placeholder – istəsən öz backend-inə bağla
USE_TRUECALLER = False  # istəsən True yap və funksiyanı özün doldur


def reset_time():
    return datetime.now().replace(
        hour=0, minute=0, second=0, microsecond=0
    ) + timedelta(days=1)


# ==================================================
#   TRUECALLER LOOKUP (SKELET)
# ==================================================
def lookup_number(number: str):

    # 1) Azercell API
    try:
        r = requests.get(AZERCELL_API + number, timeout=5)
        j = r.json()
        owner = j.get("owner") or j.get("name") or j.get("fullname")
        if owner:
            return owner, {"source": "Azercell", "raw": j}
    except:
        pass

    # 2) Kahin API
    try:
        r = requests.get(KAHIN_API + number, timeout=5)
        j = r.json()
        name = j.get("name") or j.get("owner")
        if name:
            return name, {"source": "Kahin", "raw": j}
    except:
        pass

    # 3) Numverify
    try:
        r = requests.get(NUMVERIFY_API + number, timeout=5)
        j = r.json()
        if j.get("valid"):
            return None, {
                "source": "Numverify",
                "country": j.get("country_name", "Bilinmiyor"),
                "carrier": j.get("carrier", "Bilinmiyor"),
                "raw": j
            }
    except:
        pass

    # 4) ZAPCALLER (DÜZGÜN GİRİNTİLİ)
    try:
        r = requests.get(ZAPCALLER_API + number, timeout=5)
        j = r.json()
        name = j.get("name") or j.get("caller") or j.get("fullname")
        if name:
            return name, {"source": "ZapCaller", "raw": j}
    except:
        pass

    return None, None

# ==================================================
#   ORTAQ AXTARIŞ FUNKSİYALARI
# ==================================================
def lookup_number(number: str):
    """
    Nömrə → (isim, əlavə_məlumat) qaytarır.
    isim tapılmasa None, extra_info dict ola bilər.
    """

    # 1) Azercell API
    try:
        r = requests.get(AZERCELL_API + number, timeout=5)
        j = r.json()
        owner = j.get("owner") or j.get("name") or j.get("fullname")
        if owner:
            return owner, {"source": "Azercell", "raw": j}
    except:
        pass

    # 2) Kahin API
    try:
        r = requests.get(KAHIN_API + number, timeout=5)
        j = r.json()
        name = j.get("name") or j.get("owner")
        if name:
            return name, {"source": "Kahin", "raw": j}
    except:
        pass

    # 3) Numverify – ölkə / operator üçün
    try:
        r = requests.get(NUMVERIFY_API + number, timeout=5)
        j = r.json()
        if j.get("valid"):
            country = j.get("country_name", "Bilinmiyor")
            carrier = j.get("carrier", "Bilinmiyor")
            # isim yoxdu, amma əlavə info var
            return None, {
                "source": "Numverify",
                "country": country,
                "carrier": carrier,
                "raw": j,
            }
    except:
        pass

    # 4) Truecaller (əgər aktiv edilibsə)
    tc_name = truecaller_lookup(number)
    if tc_name:
        return tc_name, {"source": "Truecaller", "raw": {"name": tc_name}}

    return None, None


def lookup_name(name_query: str):
    """
    İsim → nömrə
    Hazırda yalnız Kahin search-dən istifadə edir.
    """
    try:
        url = "https://kahin.org/api/search?name=" + name_query.lower()
        r = requests.get(url, timeout=5)
        j = r.json()
        if j and "number" in j:
            return j["number"], j
    except:
        pass

    return None, None


# ==================================================
#   BÜTÜN HANDLERLƏRİ YAZAN ORTAQ FUNKSİYA
#   is_main=True → klonlama, butonlar aktiv
# ==================================================
def register_handlers(dp: Dispatcher, is_main: bool):

        # ================== /start ==================
    @dp.message(Command("start"))
    async def start_cmd(msg: types.Message):
        uid = msg.from_user.id
        user = msg.from_user.username or msg.from_user.first_name

        if uid not in users:
            users[uid] = {"count": 0, "reset": reset_time(), "refs": 0}

        args = msg.text.split()

        # Referans sistemi
        if len(args) > 1 and args[1].startswith("ref_"):
            ref_id = int(args[1].replace("ref_", ""))

            if ref_id != uid and ref_id in users:
                users[ref_id]["refs"] += 1
                await msg.answer(
                    f"🎉 @{user} referans ile giriş yaptı!\n"
                    f"Referans sahibine +1 ek sorgu hakkı verildi."
                )

        total_limit = BASE_LIMIT + users[uid]["refs"]

        # ==============================
        # 📌 KLAVYATURA (BUTONLAR)
        # ==============================
        if is_main:
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🔧 Bot Oluştur (Klonla)",
                            callback_data="create_bot"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="📨 Referans Linkim",
                            callback_data=f"show_ref_{uid}"
                        )
                    ]
                ]
            )
        else:
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="📨 Referans Linkim",
                            callback_data=f"show_ref_{uid}"
                        )
                    ]
                ]
            )

        # ==============================
        # 📌 MESAJ MƏTNİ
        # ==============================
        text = (
            f"👋 Merhaba <b>{user}</b>!\n\n"
            f"📅 Kayıt Tarihiniz: <b>{datetime.now().date()}</b>\n"
            f"🔍 Günlük Sorgu Limitiniz: <b>{total_limit}</b>\n"
            f"⏳ Limit her gece otomatik sıfırlanır.\n\n"
            f"🤝 Referans Sistemi:\n"
            f"• Her davet = <b>+1 sorgu hakkı</b>\n\n"
            f"📋 Kullanım:\n"
            f"• Numara yaz (502022001)\n"
            f"• İsim Soyisim yaz (Əhməd Məmmədov)\n"
            f"• Rastgele: /random\n"
        )

        await msg.answer(text, reply_markup=keyboard)

    # =======================================
    # 📨 REFERANS LINKİ CALL BACK
    # =======================================
    @dp.callback_query(lambda c: c.data.startswith("show_ref_"))
    async def show_ref(call: types.CallbackQuery):
        uid = call.from_user.id
        await call.message.answer(
            f"📨 Referans linkiniz:\n"
            f"<code>t.me/AzeOsint_bot?start=ref_{uid}</code>"
        )
        await call.answer()


        if is_main:
            text += "\n✨ Kendi botunu oluşturmak için aşağıdaki butonu kullan."
        else:
            text += "\n🤖 Bu bot AzeOsint sisteminin klonlanmış bir örneğidir."

        await msg.answer(text, reply_markup=keyboard)

    # ================== /help ==================
    @dp.message(Command("help"))
    async def help_cmd(msg: types.Message):
        uid = msg.from_user.id
        if uid not in users:
            users[uid] = {"count": 0, "reset": reset_time(), "refs": 0}

        total_limit = BASE_LIMIT + users[uid]["refs"]

        await msg.answer(
            "❓ <b>Yardım Menüsü</b>\n\n"
            f"• Günlük limitiniz: <b>{total_limit}</b>\n"
            f"• Her referans = +1 sorgu hakkı\n"
            f"• Rastgele sorgu: /random\n"
            f"• Numara → İsim: sadece numara yaz\n"
            f"• İsim → Numara: sadece isim yaz"
            f"• /stats Komutu Sayesinde Statiklerinizi Göre Bilirsiniz"
        )

    # ================== /random ==================
    @dp.message(Command("random"))
    async def random_cmd(msg: types.Message):
        import random

        # Random Azercell aralığı örnək (istəsən dəqiqləşdir)
        num = str(random.randint(500000000, 559999999))

        full_number = "994" + num  # ölkə kodu ilə

        name, info = lookup_number(full_number)

        if name:
            return await msg.answer(
                f"🎲 Rastgele Sonuç:\n"
                f"📞 {full_number}\n"
                f"👤 İsim: {name}\n"
                f"ℹ Kaynak: {info.get('source') if info else 'Bilinmiyor'}"
            )

        # İsim çıxmasa, əlavə info varsa onu göstər
        if info:
            return await msg.answer(
                f"🎲 Rastgele Sonuç:\n"
                f"📞 {full_number}\n"
                f"🌍 Ülke: {info.get('country', 'Bilinmiyor')}\n"
                f"📡 Operatör: {info.get('carrier', 'Bilinmiyor')}\n"
                f"⚠ İsim bulunamadı."
            )

        await msg.answer(
            f"🎲 Rastgele Sonuç:\n"
            f"📞 {full_number}\n"
            "❌ Bu numara hakkında hiçbir veri bulunamadı."
        )

    # ================== KLON TƏLİMATI (yalnız ANA botda) ==================
    if is_main:

        @dp.callback_query(lambda c: c.data == "create_bot")
        async def bot_create_instructions(call: types.CallbackQuery):

            instructions = (
                "🔧 <b>Bot Oluşturma Talimatı</b>\n\n"
                "1. Telegram'da @BotFather'ı aç\n"
                "2. 'Start' tuşuna bas veya /start yaz\n"
                "3. Komut yaz: <b>/newbot</b>\n"
                "4. Botuna bir isim ver\n"
                "5. Sonu 'bot' ile biten bir username seç\n"
                "6. BotFather sana bir <b>API Token</b> gönderecek\n\n"
                "🔑 Örnek Token:\n"
                "<code>1234567890:ABC-DEF1234ghIkl-zyx57W2v1u123ew11</code>\n\n"
                "📩 Bu tokeni buraya gönder → Botun otomatik klonlanacak! 🔥"
            )

            await call.message.answer(instructions)
            await call.answer()

        # ================== TOKEN ALGILAMA → KLONLAMA ==================
        @dp.message(lambda msg: msg.text and ":" in msg.text and len(msg.text) > 20)
        async def auto_clone(msg: types.Message):
            token = msg.text.strip()

            await msg.answer("⏳ Token alındı, klonlama başlatılıyor...")

            try:
                await start_clone_bot(token)
                await msg.answer(
                    "✅ <b>Bot başarıyla klonlandı!</b>\n"
                    f"🔑 Token: <code>{token}</code>\n"
                    "🔥  Bot şu anda aktif."
                )
            except Exception as e:
                await msg.answer(f"❌ Klonlama hatası: {e}")

    # ================== ANA ARAMA SİSTEMİ ==================
    @dp.message()
    async def search(msg: types.Message):
        uid = msg.from_user.id
        q = msg.text.strip()

        if uid not in users:
            users[uid] = {"count": 0, "reset": reset_time(), "refs": 0}

        data = users[uid]
        now = datetime.now()

        # Reset zamanı
        if now >= data["reset"]:
            data["count"] = 0
            data["reset"] = reset_time()

        total_limit = BASE_LIMIT + data["refs"]

        if data["count"] >= total_limit:
            return await msg.answer("⛔ Günlük sorgu limitiniz doldu.")

        data["count"] += 1

        # ---------- NUMARA → İSİM ----------
        if q.isdigit():
            full_number = q
            # Əgər istifadəçi 9 rəqəm yazırsa, avtomatik 994 əlavə edə bilərsən
            if len(q) == 9:
                full_number = "994" + q

            name, info = lookup_number(full_number)

            if name:
                src = info.get("source") if info else "Bilinmiyor"
                return await msg.answer(
                    f"📞 Numara: {full_number}\n"
                    f"👤 İsim: {name}\n"
                    f"ℹ Kaynak: {src}"
                )

            if info:
                return await msg.answer(
                    f"📞 Numara: {full_number}\n"
                    f"🌍 Ülke: {info.get('country', 'Bilinmiyor')}\n"
                    f"📡 Operatör: {info.get('carrier', 'Bilinmiyor')}\n"
                    "⚠ İsim bulunamadı."
                )

            return await msg.answer("❌ Bu numara hakkında hiçbir veri bulunamadı.")

        # ---------- İSİM → NUMARA ----------
        number, raw = lookup_name(q)
        if number:
            return await msg.answer(
                f"👤 İsim: {q.title()}\n"
                f"📞 Numara: {number}"
            )

        await msg.answer("❌ Hiçbir sonuç bulunamadı.")

    # ================== /stats ==================
    @dp.message(Command("stats"))
    async def stats_cmd(msg: types.Message):
        uid = msg.from_user.id

        if uid not in users:
            users[uid] = {"count": 0, "reset": reset_time(), "refs": 0}

        data = users[uid]

        bugun_say = data["count"]
        limit = BASE_LIMIT + data["refs"]
        qalan = limit - bugun_say

        # Resetə qalan vaxt
        now = datetime.now()
        qalan_vaxt = data["reset"] - now
        saat = qalan_vaxt.seconds // 3600
        deqiqe = (qalan_vaxt.seconds % 3600) // 60

        await msg.answer(
            f"📊 <b>Statistikalarınız</b>\n\n"
            f"📅 Qeydiyyat tarixi: <b>{datetime.now().date()}</b>\n"
            f"🔍 Bugünkü sorğular: <b>{bugun_say}/{limit}</b>\n"
            f"📈 Qalan sorğular: <b>{qalan}</b>\n"
            f"⏳ Limit yenilənməsinə: <b>{saat} saat {deqiqe} dəqiqə</b>\n"
            f"🕐 Son sorğu: <b>{datetime.now().strftime('%Y-%m-%d %H:%M')}</b>"
        )

# ==================================================
#   KLON BOT BAŞLATICI
# ==================================================
async def start_clone_bot(new_token: str):
    clone_bot = Bot(
        token=new_token,
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    clone_dp = Dispatcher()

    # Klon bot üçün də eyni handler-ləri yazırıq
    register_handlers(clone_dp, is_main=False)

    print(f"[KLON BOT AKTİF] TOKEN: {new_token}")
    asyncio.create_task(clone_dp.start_polling(clone_bot))


# ==================================================
#   ANA BOT
# ==================================================
async def main():
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    dp = Dispatcher()

    # Handlerləri qeyd edirik
    register_handlers(dp, is_main=True)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
