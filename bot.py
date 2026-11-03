@app.route('/claim')
def claim():
    user_id = request.args.get('user_id')
    seconds = request.args.get('seconds')
    
    if user_id and seconds:
        try:
            user_id = int(user_id)
            raw_points = int(float(seconds))
            
            if is_user_banned(user_id):
                return "OK", 200

            if 0 < raw_points <= 60:
                is_boosted = time.time() < get_boost_end_time(user_id)
                final_points = raw_points * 2 if is_boosted else raw_points
                
                update_balance(user_id, final_points)
                boost_text = " (x2)" if is_boosted else ""
                bot.send_message(user_id, f"✅ Намайнил {final_points} SFP{boost_text}.\nБаланс: {get_balance(user_id):.1f} SFP")
                
                referrer = get_referrer(user_id)
                if referrer and referrer != user_id:
                    ref_bonus = int(final_points * 0.10)
                    if ref_bonus > 0:
                        update_balance(referrer, ref_bonus)
                        try: bot.send_message(referrer, f"💸 Реферал намайнил {final_points} SFP. Тебе +{ref_bonus} SFP.")
                        except: pass
            else:
                ban_user(user_id)
        except Exception as e:
            print(f"Ошибка claim: {e}")
            
    return "OK", 200
