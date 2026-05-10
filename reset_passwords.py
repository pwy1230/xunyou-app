"""Reset all user passwords on PythonAnywhere"""
import sys
sys.path.insert(0, '/home/13800138000/xunyou-app')
from app import app, db
from werkzeug.security import generate_password_hash

with app.app_context():
    # Reset real test users
    test_users = {
        '13800138000': 'admin123',
        '13800138004': '123456',
    }
    for phone, pwd in test_users.items():
        pw_hash = generate_password_hash(pwd)
        db.session.execute(db.text('UPDATE users SET password_hash=:h WHERE phone=:p'), {'h': pw_hash, 'p': phone})
        print(f'Updated {phone}')
    
    # Reset all fake/seed female users to 123456
    fake_hash = generate_password_hash('123456')
    db.session.execute(db.text("UPDATE users SET password_hash=:h WHERE phone LIKE 'fake_%'"), {'h': fake_hash})
    print('Updated all fake users')
    
    # Give male user coins
    db.session.execute(db.text("UPDATE users SET coin_balance=9999 WHERE phone='13800138004'"))
    print('Gave male user 9999 coins')
    
    # Also give the registered test male user coins
    db.session.execute(db.text("UPDATE users SET coin_balance=9999 WHERE phone='13900001111'"))
    print('Gave 13900001111 9999 coins')
    
    db.session.commit()
    print('Done!')
