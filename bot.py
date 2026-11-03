if points > 0 and points <= 60:
                update_balance(user_id, points)
                new_balance = get_balance(user_id)
                bot.send_message(user_id, f"✅ Успешно! Ты намайнил {points} SFP.\nТвой новый баланс: {new_balance:.1f} SFP")
            else:
                # БАНИМ ЗА НАКРУТКУ
                ban_user(user_id)
                print(f"🚫 Пользователь {user_id} забанен за накрутку ({points} сек).")
                try:
                    bot.send_message(user_id, "⛔ Ты заблокирован за попытку взлома системы.")
                except:
                    pass
                
        except Exception as e:
            print(f"Ошибка: {e}")
            
    return "OK", 200

@app.route('/' + t, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url=f'https://focus-mine-bot.onrender.com/{t}')
    return "Webhook установлен!", 200

app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
