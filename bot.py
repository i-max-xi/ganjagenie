from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButton, ReplyKeyboardMarkup
)
from datetime import datetime
from dotenv import load_dotenv
import os

from telegram.ext import (
    Updater, CommandHandler, CallbackQueryHandler,
    MessageHandler, CallbackContext
)
from telegram.ext.filters import Filters  # This line should now be like this.
import random
import re

load_dotenv()
TOKEN = os.getenv('TOKEN')
ADMIN_USER_ID = os.getenv('ADMIN_USER_ID')



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

# In-memory per-user session
user_data = {}

def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id

    # Only reset if user is new
    if user_id not in user_data:
        user_data[user_id] = {'cart': [], 'phone': None, 'location': None}

    keyboard = [
        [InlineKeyboardButton(cat, callback_data=f"category:{cat}")]
        for cat in PRODUCTS
    ]

    if update.message:
        update.message.reply_text(
            "🛍 Welcome! Choose a category:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif update.callback_query:
        update.callback_query.message.reply_text(
            "🛍 Welcome back! Choose a category:",
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
                    [InlineKeyboardButton(f"Buy 3x @ GH₵{product['price']['3x']}",
                                          callback_data=f"buy:{product['name']}:3x:{product['price']['3x']}")],
                    [InlineKeyboardButton(f"Buy 6x @ GH₵{product['price']['6x']}",
                                          callback_data=f"buy:{product['name']}:6x:{product['price']['6x']}")]
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
            buttons = [
                [InlineKeyboardButton("✅ Checkout", callback_data="checkout")],
                [InlineKeyboardButton("🔁 Continue Shopping", callback_data="start_over")]
            ]
            context.bot.send_message(
                chat_id=query.message.chat_id,
                text="🧾 What would you like to do next?",
                reply_markup=InlineKeyboardMarkup(buttons)
            )

        elif query.data == "checkout":
            context.bot.send_message(
                chat_id=query.message.chat_id,
                text="📞 Please type your phone number in format 233XXXXXXXXX:"
            )

        elif query.data == "start_over":
            start(update, context)

        elif query.data == "send_order":
            complete_order(query, context, user_id)

    except Exception as e:
        context.bot.send_message(chat_id=query.message.chat_id, text="❌ Something went wrong.")
        print(f"Error handling callback: {e}")

def handle_text(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if text.lower() == "send order":
        complete_order(update.message, context, user_id)
    elif re.fullmatch(r'233\d{9}', text):
        user_data[user_id]['phone'] = text
        location_button = KeyboardButton("📍 Send Location", request_location=True)
        update.message.reply_text(
            "📍 Now send your delivery location:",
            reply_markup=ReplyKeyboardMarkup([[location_button]], resize_keyboard=True, one_time_keyboard=True)
        )
    else:
        update.message.reply_text("❗ Invalid input. Please type a valid phone number (233XXXXXXXXX)")

def handle_location(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    location = update.message.location
    if location:
        user_data[user_id]['location'] = location
        buttons = [[InlineKeyboardButton("📤 Submit Order", callback_data="send_order")]]
        update.message.reply_text(
            "✅ Location received. Ready to place your order?",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    else:
     update.message.reply_text("❗ Could not retrieve location. Please try again.")

def complete_order(source, context: CallbackContext, user_id):
    cart = user_data[user_id]['cart']
    phone = user_data[user_id]['phone']
    location = user_data[user_id]['location']

    # Determine reply method
    if hasattr(source, 'message'):
        # Called from a CallbackQuery
        chat_id = source.message.chat_id
        send = lambda text, **kwargs: context.bot.send_message(chat_id=chat_id, text=text, **kwargs)
    else:
        # Called from a Message
        send = lambda text, **kwargs: source.reply_text(text, **kwargs)

    if not cart:
        send("🛒 Your cart is empty.")
        return
    if not phone:
        send("📞 Please provide your phone number first.")
        return
    if not location:
        send("📍 Please send your location first.")
        return

    total = sum(item['price'] for item in cart)
    lines = [f"{idx+1}. {item['qty']} {item['name']}" for idx, item in enumerate(cart)]
    timestamp = datetime.now().strftime("%y%m%d-%H%M%S")
    user_part = str(user_id)[-4:]  # last 4 digits of user ID
    order_no = f"ORD-{timestamp}-{user_part}"
    summary = (
        f"Your order has been sent.\n"
        f"Your Order Number is *{order_no}*\n\n"
        f"*PLEASE NOTE:*\n"
        f"1. A dispatch rider will call you to confirm your order, location and delivery charge.\n"
        f"2. Please send your payment to 024XXXXXXX (Owner) to confirm your order. Items will *NOT* be sent until payment is received.\n"
        f"3. Use your *Order Number* as the *Reference*.\n"
        f"4. Any errors on your part may result in you not receiving your order.\n"
        f"5. For safety reasons, orders placed after 6pm may not be delivered until the next day.\n\n"
        f"*️⃣ Order Summary:*\n"
        f"`Contact: {phone}`\n"
        f"`Location: {location.latitude}, {location.longitude}`\n"
        f"`Products:`\n" + "\n".join(lines) + f"\n\n*Total: GH₵{total}*"
    )

    send(summary, parse_mode='Markdown')
    send("🛒 Your cart has been cleared.\n\nCheckout our products with /start")

    # Send order to the admin
    admin_message = (
        f"New Order!\n\n"
        f"Order Number: *{order_no}*\n"
        f"Contact: {phone}\n"
        f"Location: {location.latitude}, {location.longitude}\n"
        f"📍 [Google Maps](https://maps.google.com/?q={location.latitude},{location.longitude})\n"
        f"Total: GH₵{total}\n\n"
        f"Order Details:\n"
        + "\n".join([f"{item['qty']} {item['name']} (GH₵{item['price']})" for item in cart]) + "\n\n"
        f"Please confirm and fulfill the order."
    )



    context.bot.send_message(chat_id=ADMIN_USER_ID, text=admin_message, parse_mode='Markdown')
    context.bot.send_location(chat_id=ADMIN_USER_ID, latitude=location.latitude, longitude=location.longitude)


    # Reset session
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
