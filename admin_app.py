from flask import Flask, render_template
import sqlite3

app = Flask(__name__)

@app.route('/admin')
def admin_panel():
    conn = sqlite3.connect('clients.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bankruptcy_applications")
    clients = cursor.fetchall()
    return render_template('admin.html', clients=clients)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=10001)