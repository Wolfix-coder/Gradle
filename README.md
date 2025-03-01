# Admin Bot

This is an administration bot built with aiogram for managing orders and users.

## Features
- Order management
- Payment processing 
- User administration
- Statistics tracking
- File handling

## Installation
1. Clone the repository
2. Install requirements: `pip install -r requirements.txt`
3. Configure environment variables in `.env`
4. Run the bot: `python src/main.py`

## Project Structure
```
📁 admin_bot/
├── 📁 src/
│ ├── 📁 handlers/      # Request handlers
│ │ ├── __init__.py
│ │ ├── admin.py
│ │ ├── orders.py
│ │ ├── payments.py
│ │ ├── statistics.py
│ │ ├── users.py
│ │ ├── basik.py
│ ├── 📁 models/        # Data models
│ │ ├── __init__.py
│ │ ├── base.py
│ │ ├── order.py
│ │ ├── user.py
│ ├── 📁 services/      # Business logic
│ │ ├── __init__.py
│ │ ├── database.py
│ │ ├── file_service.py
│ │ ├── order_service.py
│ │ ├── payment_service.py
│ │ ├── user_service
│ ├── 📁 utils/         # Helper functions
│ │ ├── __init__.py
│ │ ├── decorators.py
│ │ ├── keyboards.py
│ │ ├── logging.py
│ │ ├── validators.py
│ ├── 📁 states/        # FSM states
│ │ ├── __init__.py
│ │ ├── order_states.py
│ │ ├── user_states.py
│ ├── __init__.py
│ ├── .env
│ ├── config.py         # Configuration
│ └── main.py          # Entry point
├── bot.log
├── database.sqlite
├── requirements.txt
└── README.md
```

## Contributing
Pull requests are welcome. For major changes, please open an issue first.

## License 
MIT