from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext
import random
import re

TOKEN = ''

# Products
PRODUCTS = {
    'Marijuana': [
        {
            'name': 'GH Gold (rolls)',
            'description': 'Premium sativa strain for energy and creativity.',
            'price': {'3x': 120, '6x': 200},
            'image': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTIQ_hu-Yscop8PrJ2o8Jgr8FnvfE6lZQCYKQ&s'
        },
        {
            'name': 'Super Kush',
            'description': 'Heavy indica. Best for relaxation and sleep.',
            'price': {'3x': 150, '6x': 250},
            'image': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcS1j_5O93Kfd_hqUKYYqZzQRhx9W2cKGpZXCQ&s'
        }
    ]
}

# In-memory user data
user_data = {}

def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user_data[user_id] = {'cart': [], 'phone': None, 'location': None}

    keyboard = [
        [InlineKeyboardButton(cat, callback_data=f"category:{cat}")]
        for cat in PRODUCTS
    ]
    update.message.reply_text(
        "🛍 Welcome! Choose a category:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def handle_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    user_id = query.from_user.id

    try:
        if query.data.startswith("category:"):
            category = query.data.split(":")[1]
            for product in PRODUCTS.get(category, []):
                buttons = [
                    [InlineKeyboardButton(f"Buy 3x @ GH₵{product['price']['3x']}", callback_data=f"buy:{product['name']}:3x:{product['price']['3x']}")],
                    [InlineKeyboardButton(f"Buy 6x @ GH₵{product['price']['6x']}", callback_data=f"buy:{product['name']}:6x:{product['price']['6x']}")]
                ]
                context.bot.send_photo(
                    chat_id=query.message.chat_id,
                    photo=product['image'],
                    caption=f"*{product['name']}*\n{product['description']}",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup(buttons)
                )

        elif query.data.startswith("buy:"):
            _, name, qty, price = query.data.split(":")
            user_data[user_id]['cart'].append({'name': name, 'qty': qty, 'price': int(price)})
            context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"🛒 Added *{qty}* of *{name}* (GH₵{price}) to your cart!",
                parse_mode='Markdown'
            )
            context.bot.send_message(
                chat_id=query.message.chat_id,
                text="Type *checkout* to continue or /start to shop more.",
                parse_mode='Markdown'
            )
    except Exception as e:
        context.bot.send_message(chat_id=query.message.chat_id, text="❌ Something went wrong.")
        print(f"Error handling callback: {e}")

def handle_text(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if text.lower() == "checkout":
        update.message.reply_text("📞 Please type your phone number in format 233XXXXXXXXX:")
    elif re.fullmatch(r'233\d{9}', text):  # phone number validation
        user_data[user_id]['phone'] = text
        location_button = KeyboardButton("📍 Send Location", request_location=True)
        update.message.reply_text(
            "📍 Now send your delivery location:",
            reply_markup=ReplyKeyboardMarkup([[location_button]], resize_keyboard=True, one_time_keyboard=True)
        )
    elif user_data[user_id].get('phone') and user_data[user_id].get('location'):
        update.message.reply_text("✅ Already received phone and location. Type 'send order' to finish.")
    elif text.lower() == "send order":
        complete_order(update, context, user_id)
    else:
        update.message.reply_text("❗ Invalid input. Please type a valid command or phone number.")

def handle_location(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    location = update.message.location
    if location:
        user_data[user_id]['location'] = location
        update.message.reply_text("✅ Location received. Type *send order* to place your order.", parse_mode='Markdown')

def complete_order(update: Update, context: CallbackContext, user_id):
    cart = user_data[user_id]['cart']
    phone = user_data[user_id]['phone']
    location = user_data[user_id]['location']
    if not (cart and phone and location):
        update.message.reply_text("⚠️ You're missing something (cart, phone, or location).")
        return

    total = sum(item['price'] for item in cart)
    lines = [f"{idx+1}. {item['qty']} {item['name']}" for idx, item in enumerate(cart)]
    order_no = random.randint(1000, 9999)

    summary = (
        f"Your order has been sent.\n"
        f"Your Order Number is *{order_no}*\n\n"
        f"*PLEASE NOTE:*\n"
        f"1. A dispatch rider will call you to confirm your order, location and delivery charge.\n"
        f"2. Please send your payment to 0508938648 (Eric) to confirm your order. Items will *NOT* be sent until payment is received\n"
        f"3. Use your *Order Number* as the *Reference*.\n"
        f"4. Any errors on your part may result in you not receiving your order.\n"
        f"5. For safety reasons, orders placed after 6pm may not be delivered until the next day.\n"
        f"6. Text us on Telegram @ *ELFRENTEROJO* for further enquiries.\n\n"
        f"*️⃣ Order Summary:*\n"
        f"`Contact: {phone}`\n"
        f"`Location: {location.latitude}, {location.longitude}`\n"
        f"`Products:`\n" + "\n".join(lines) + f"\n\n*Total: GH₵{total}*"
    )

    update.message.reply_text(summary, parse_mode='Markdown')
    update.message.reply_text("🛒 Your cart has been cleared.\n\nCheckout our products with /start")

    # Clear user session
    user_data[user_id] = {'cart': [], 'phone': None, 'location': None}

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(handle_callback))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
    dp.add_handler(MessageHandler(Filters.location, handle_location))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
