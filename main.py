# --- Запуск ---
def main():
    """Головна функція для налаштування та запуску бота."""
    app_telegram = (
        ApplicationBuilder()
        .token(TOKEN)
        .build()
    )

    # Додавання обробників (handlers) у правильному порядку
    
    # 1. Обробник команди /start
    app_telegram.add_handler(CommandHandler("start", start))
    
    # 2. Обробник для кнопок "Так" / "Ні" (БІЛЬШ КОНКРЕТНИЙ, тому він ПЕРШИЙ)
    app_telegram.add_handler(MessageHandler(filters.Regex("^(Так|Ні)$"), handle_reminder_choice))
    
    # 3. Обробник для всіх інших текстових повідомлень (БІЛЬШ ЗАГАЛЬНИЙ, тому він ДРУГИЙ)
    app_telegram.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_data))

    # Запускаємо планувальник. Він інтегрується з event loop, який створить run_polling()
    scheduler.start()
    print("✅ Бот запущений")

    # Запускаємо полінг. run_polling() сам керує event loop і є блокуючим викликом
    app_telegram.run_polling()


if __name__ == "__main__":
    # Запускаємо головну функцію напряму, без asyncio.run()
    main()
