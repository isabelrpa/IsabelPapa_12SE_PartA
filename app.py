from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import os
import time
from functools import wraps

app = Flask(__name__)
app.secret_key='ISA12_SE'

# Configuration
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# AUTHENTICATION ROUTES

# LOGIN PAGE
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = sqlite3.connect('part_a.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM Users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Invalid username or password')
    
    return render_template('login.html')

# REGISTER PAGE
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            return render_template('login.html', error='Passwords do not match', show_register=True)
        
        hashed_password = generate_password_hash(password)
        
        conn = sqlite3.connect('part_a.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute('INSERT INTO Users (username, password) VALUES (?, ?)',
                         (username, hashed_password))
            conn.commit()
            
            # Get the new user's ID
            user_id = cursor.lastrowid
            
            # COPY STARTER TRIPS FROM USER_ID 1 TO NEW USER
            cursor.execute('''
                INSERT INTO Trips (trip_location, trip_start, trip_end, trip_image, trip_description, rating, user_id)
                SELECT trip_location, trip_start, trip_end, trip_image, trip_description, rating, ?
                FROM Trips
                WHERE user_id = 1
            ''', (user_id,))
            
            # Copy journal entries for the new trips
            cursor.execute('SELECT trip_id FROM Trips WHERE user_id = ? ORDER BY trip_id', (user_id,))
            new_trip_ids = [row[0] for row in cursor.fetchall()]
            
            cursor.execute('SELECT trip_id FROM Trips WHERE user_id = 1 ORDER BY trip_id')
            old_trip_ids = [row[0] for row in cursor.fetchall()]
            
            # Copy journal entries
            for old_id, new_id in zip(old_trip_ids, new_trip_ids):
                cursor.execute('''
                    INSERT INTO Journal (entry_date, journal_entry, trip_id)
                    SELECT entry_date, journal_entry, ?
                    FROM Journal
                    WHERE trip_id = ?
                ''', (new_id, old_id))
            
            # Copy album photos
            for old_id, new_id in zip(old_trip_ids, new_trip_ids):
                cursor.execute('''
                    INSERT INTO Album (photo_path, photo_alt, trip_id, date_added)
                    SELECT photo_path, photo_alt, ?, date_added
                    FROM Album
                    WHERE trip_id = ?
                ''', (new_id, old_id))
            
            conn.commit()
            conn.close()
            
            # Log them in automatically
            session['user_id'] = user_id
            session['username'] = username
            
            return redirect(url_for('index'))
        except sqlite3.IntegrityError:
            conn.close()
            return render_template('login.html', error='Username already exists', show_register=True)
    
    return render_template('login.html', show_register=True)

# LOGOUT
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ROUTES

# HOME PAGE (DISPLAY ALL TRIPS)
@app.route('/')
@login_required
def index():
    # Get sort parameter
    sort_by = request.args.get('sort', 'id_desc')
    
    # Connect to database
    conn = sqlite3.connect('part_a.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Determine sort order (based on option selected by user)
    if sort_by == 'date_asc':
        order_clause = 'ORDER BY trip_start ASC'
    elif sort_by == 'date_desc':
        order_clause = 'ORDER BY trip_start DESC'
    elif sort_by == 'id_asc':
        order_clause = 'ORDER BY trip_id ASC'
    elif sort_by == 'id_desc':
        order_clause = 'ORDER BY trip_id DESC'
    elif sort_by == 'location_asc':
        order_clause = 'ORDER BY trip_location COLLATE NOCASE ASC'
    elif sort_by == 'rating_asc':
        order_clause = 'ORDER BY rating ASC, trip_id DESC'
    elif sort_by == 'rating_desc':
        order_clause = 'ORDER BY rating DESC, trip_id DESC'
    else:
        order_clause = 'ORDER BY trip_id DESC'
    
    # Fetch trips for logged-in user only
    query = f'SELECT * FROM Trips WHERE user_id = ? {order_clause}'
    cursor.execute(query, (session['user_id'],))
    all_trips = cursor.fetchall()
    conn.close()
    
    return render_template('index.html', trips=all_trips)



# VIEW INDIVIDUAL TRIP DETAILS
@app.route('/trip/<int:trip_id>')
@login_required
def trip(trip_id):
    # Get trip details
    conn = sqlite3.connect('part_a.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM Trips WHERE trip_id = ? AND user_id = ?', (trip_id, session['user_id']))
    trip = cursor.fetchone()
    conn.close()
    
    if trip is None:
        return "Trip not found", 404
    
    return render_template('trip.html', trip=trip)



# CREATE (NEW) TRIP
@app.route('/create', methods=['POST', 'GET'])
@login_required
def create():
    if request.method == 'POST':
        # Get trip form data
        trip_location = request.form.get('trip_location')
        trip_start = request.form.get('trip_start')
        trip_end = request.form.get('trip_end')
        trip_description = request.form.get('trip_description')
        rating = request.form.get('rating')
        
        # Handle image upload
        if 'trip_image' not in request.files:
            return "No file uploaded", 400
        
        file = request.files['trip_image']
        
        if file.filename == '':
            return "No file selected", 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filename = f"{int(time.time())}_{filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            trip_image = f"uploads/{filename}"
        else:
            return "Invalid file type. Please upload PNG, JPG, JPEG, GIF, or WEBP", 400

        # Insert into database with user_id
        conn = sqlite3.connect('part_a.db')
        cursor = conn.cursor()

        cursor.execute('''
        INSERT INTO Trips (trip_location, trip_start, trip_end, trip_image, trip_description, rating, user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (trip_location, trip_start, trip_end, trip_image, trip_description, rating, session['user_id']))
        conn.commit()
        conn.close()
        
        return redirect(url_for('index'))
    
    return render_template('form.html')



# UPDATE (EXISTING) TRIP
@app.route('/update/<int:trip_id>', methods=['POST','GET'])
@login_required
def update(trip_id):
    conn = sqlite3.connect('part_a.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if request.method == 'POST':
        # Get form data
        trip_location = request.form.get('trip_location')
        trip_start = request.form.get('trip_start')
        trip_end = request.form.get('trip_end')
        trip_description = request.form.get('trip_description')
        rating = request.form.get('rating')

        import re
        from datetime import datetime
        
        # Validate location
        if not re.match(r'^[a-zA-Z\s,.-]+$', trip_location):
            conn.close()
            return "Invalid location format. Only letters, spaces, commas, periods, and hyphens allowed.", 400
        
        # Validate dates
        try:
            start = datetime.strptime(trip_start, '%Y-%m-%d')
            end = datetime.strptime(trip_end, '%Y-%m-%d')
            if end < start:
                conn.close()
                return "End date must be after start date.", 400
        except ValueError:
            conn.close()
            return "Invalid date format.", 400
        
        # Validate description length
        if trip_description and len(trip_description) > 250:
            conn.close()
            return "Description must be 250 characters or less.", 400
        
        # Validate rating
        try:
            rating_int = int(rating)
            if rating_int < 1 or rating_int > 5:
                conn.close()
                return "Rating must be between 1 and 5.", 400
        except (ValueError, TypeError):
            conn.close()
            return "Invalid rating. Please select a rating.", 400

        # Handle image upload
        if 'trip_image' in request.files and request.files['trip_image'].filename != '':
            file = request.files['trip_image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filename = f"{int(time.time())}_{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                trip_image = f"uploads/{filename}"
            else:
                conn.close()
                return "Invalid file type. Please upload PNG, JPG, JPEG, GIF, or WEBP", 400
        else:
            # Keep existing image
            cursor.execute('SELECT trip_image FROM Trips WHERE trip_id = ? AND user_id = ?', (trip_id, session['user_id']))
            result = cursor.fetchone()
            trip_image = result['trip_image'] if result else None

        # Update database
        cursor.execute('''
            UPDATE Trips 
            SET trip_location = ?, 
                trip_start = ?, 
                trip_end = ?, 
                trip_image = ?,
                trip_description = ?,
                rating = ?
            WHERE trip_id = ? AND user_id = ?
        ''', (trip_location, trip_start, trip_end, trip_image, trip_description, rating, trip_id, session['user_id']))

        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    
    else:
        # Get existing trip data
        cursor.execute('SELECT * FROM Trips WHERE trip_id = ? AND user_id = ?', (trip_id, session['user_id']))
        trip = cursor.fetchone()
        conn.close()

        if trip is None:
            return "Trip not found", 404
        
        return render_template('update.html', trip=trip)



# DELETE TRIP
@app.route('/delete/<int:trip_id>')
@login_required
def delete(trip_id):
    conn = sqlite3.connect('part_a.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM Trips WHERE trip_id=? AND user_id=?', (trip_id, session['user_id']))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))



# VIEW JOURNAL ENTRIES FOR TRIP
@app.route('/journal/<int:trip_id>', methods=['GET', 'POST'])
@login_required
def journal(trip_id):
    conn = sqlite3.connect('part_a.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Verify trip belongs to user
    cursor.execute('SELECT * FROM Trips WHERE trip_id = ? AND user_id = ?', (trip_id, session['user_id']))
    trip = cursor.fetchone()
    
    if trip is None:
        conn.close()
        return "Trip not found", 404
    
    if request.method == 'POST':
        # Add new journal entry
        entry_date = request.form.get('entry_date')
        journal_entry = request.form.get('journal_entry')
        
        cursor.execute(
            'INSERT INTO Journal (entry_date, journal_entry, trip_id) VALUES (?, ?, ?)',
            (entry_date, journal_entry, trip_id)
        )
        conn.commit()
        conn.close()
        
        return redirect(url_for('journal', trip_id=trip_id))
    
    # Get sort parameter
    sort_by = request.args.get('sort', 'date_desc')
    
    # Determine sort order
    if sort_by == 'date_asc':
        order_clause = 'ORDER BY entry_date ASC'
    elif sort_by == 'date_desc':
        order_clause = 'ORDER BY entry_date DESC'
    else:
        order_clause = 'ORDER BY entry_date DESC'
    
    # Get journal entries with sort
    query = f'SELECT entry_date, journal_entry, journal_id FROM Journal WHERE trip_id = ? {order_clause}'
    cursor.execute(query, (trip_id,))
    entries = cursor.fetchall()
    
    conn.close()

    return render_template('journal.html', entries=entries, trip=trip, trip_id=trip_id)




# CREATE (NEW) JOURNAL ENTRY
@app.route('/journal/add/<int:trip_id>', methods=['GET', 'POST'])
@login_required
def new_entry(trip_id):
    # Verify trip belongs to user
    conn = sqlite3.connect('part_a.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM Trips WHERE trip_id = ? AND user_id = ?', (trip_id, session['user_id']))
    trip = cursor.fetchone()
    conn.close()
    
    if trip is None:
        return "Trip not found", 404
    
    if request.method == 'POST':
        # Get form data
        entry_date = request.form.get('entry_date')
        journal_entry = request.form.get('journal_entry')
        
        # Insert into database
        conn = sqlite3.connect('part_a.db')
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO Journal (entry_date, journal_entry, trip_id) VALUES (?, ?, ?)',
            (entry_date, journal_entry, trip_id)
        )
        conn.commit()
        conn.close()
        
        return redirect(url_for('journal', trip_id=trip_id))
    
    return render_template('new_entry.html', trip_id=trip_id)



# UPDATE (EXISTING) JOURNAL ENTRY
@app.route('/journal/update/<int:entry_id>', methods=['GET', 'POST'])
@login_required
def update_journal_entry(entry_id):
    conn = sqlite3.connect('part_a.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Verify entry belongs to user's trip
    cursor.execute('''
        SELECT Journal.*, Trips.user_id 
        FROM Journal 
        JOIN Trips ON Journal.trip_id = Trips.trip_id 
        WHERE Journal.journal_id = ?
    ''', (entry_id,))
    entry = cursor.fetchone()
    
    if entry is None or entry['user_id'] != session['user_id']:
        conn.close()
        return "Journal entry not found", 404
    
    if request.method == 'POST':
        # Get form data
        entry_date = request.form.get('entry_date')
        journal_entry = request.form.get('journal_entry')
        
        # Update database
        cursor.execute('''
            UPDATE Journal 
            SET entry_date = ?, journal_entry = ?
            WHERE journal_id = ?
        ''', (entry_date, journal_entry, entry_id))
        
        conn.commit()
        conn.close()
        
        # Return success for AJAX requests
        if request.headers.get('Content-Type') == 'application/x-www-form-urlencoded':
            return '', 200
        
        # Get trip_id for redirect (if not AJAX)
        trip_id = entry['trip_id']
        
        return redirect(url_for('journal', trip_id=trip_id))
    
    else:
        # GET request - render form (keep this for fallback)
        conn.close()
        
        if entry is None:
            return "Journal entry not found", 404
        
        return render_template('update_journal_entry.html', entry=entry)



# DELETE JOURNAL ENTRY
@app.route('/journal/delete/<int:entry_id>')
@login_required
def delete_journal_entry(entry_id):
    conn = sqlite3.connect('part_a.db')
    cursor = conn.cursor()
    
    # Get trip_id and verify ownership before deleting
    cursor.execute('''
        SELECT Journal.trip_id, Trips.user_id 
        FROM Journal 
        JOIN Trips ON Journal.trip_id = Trips.trip_id 
        WHERE Journal.journal_id = ?
    ''', (entry_id,))
    result = cursor.fetchone()
    
    if result is None or result[1] != session['user_id']:
        conn.close()
        return "Journal entry not found", 404
    
    trip_id = result[0]
    
    # Delete entry
    cursor.execute('DELETE FROM Journal WHERE journal_id = ?', (entry_id,))
    conn.commit()
    conn.close()
    
    return redirect(url_for('journal', trip_id=trip_id))



# VIEW PHOTO ALBUM FOR TRIP
@app.route('/album/<int:trip_id>')
@login_required
def album(trip_id):
    conn = sqlite3.connect('part_a.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get trip details and verify ownership
    cursor.execute('SELECT * FROM Trips WHERE trip_id = ? AND user_id = ?', (trip_id, session['user_id']))
    trip = cursor.fetchone()
    
    if trip is None:
        conn.close()
        return "Trip not found", 404
    
    # Get ALL photos for this trip, ordered by most recent first (NO LIMIT)
    cursor.execute('''
        SELECT * FROM Album 
        WHERE trip_id = ? 
        ORDER BY date_added DESC
    ''', (trip_id,))
    photos = cursor.fetchall()
    
    conn.close()
    
    return render_template('album.html', trip=trip, trip_id=trip_id, photos=photos)


# UPLOAD PHOTO TO ALBUM
@app.route('/album/<int:trip_id>/upload', methods=['POST'])
@login_required
def upload_photo(trip_id):
    # Verify trip ownership
    conn = sqlite3.connect('part_a.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM Trips WHERE trip_id = ? AND user_id = ?', (trip_id, session['user_id']))
    trip = cursor.fetchone()
    conn.close()
    
    if trip is None:
        return "Trip not found", 404
    
    if 'photo' not in request.files:
        return "No file uploaded", 400
    
    file = request.files['photo']
    
    if file.filename == '':
        return "No file selected", 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filename = f"{int(time.time())}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        photo_path = f"uploads/{filename}"
        
        # Get current date
        from datetime import datetime
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        # Insert into Album table
        conn = sqlite3.connect('part_a.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO Album (photo_path, photo_alt, trip_id, date_added)
            VALUES (?, ?, ?, ?)
        ''', (photo_path, 'Uploaded photo', trip_id, current_date))
        conn.commit()
        conn.close()
        
        return redirect(url_for('album', trip_id=trip_id))
    else:
        return "Invalid file type. Please upload PNG, JPG, JPEG, GIF, or WEBP", 400


# UPDATE PHOTO IN ALBUM
@app.route('/album/update/<int:photo_id>', methods=['GET', 'POST'])
@login_required
def update_photo(photo_id):
    conn = sqlite3.connect('part_a.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Verify photo belongs to user's trip
    cursor.execute('''
        SELECT Album.*, Trips.user_id 
        FROM Album 
        JOIN Trips ON Album.trip_id = Trips.trip_id 
        WHERE Album.photo_id = ?
    ''', (photo_id,))
    photo = cursor.fetchone()
    
    if photo is None or photo['user_id'] != session['user_id']:
        conn.close()
        return "Photo not found", 404
    
    if request.method == 'POST':
        # Handle photo replacement
        if 'photo' not in request.files or request.files['photo'].filename == '':
            conn.close()
            return "No file selected", 400
        
        file = request.files['photo']
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filename = f"{int(time.time())}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            photo_path = f"uploads/{filename}"
            
            # Get current date
            from datetime import datetime
            current_date = datetime.now().strftime('%Y-%m-%d')
            
            # Update database
            cursor.execute('''
                UPDATE Album 
                SET photo_path = ?, date_added = ?
                WHERE photo_id = ?
            ''', (photo_path, current_date, photo_id))
            
            conn.commit()
            
            trip_id = photo['trip_id']
            conn.close()
            
            return redirect(url_for('album', trip_id=trip_id))
        else:
            conn.close()
            return "Invalid file type. Please upload PNG, JPG, JPEG, GIF, or WEBP", 400
    
    else:
        # GET request
        conn.close()
        
        return render_template('update_photo.html', photo=photo)


# DELETE PHOTO FROM ALBUM
@app.route('/album/delete/<int:photo_id>')
@login_required
def delete_photo(photo_id):
    conn = sqlite3.connect('part_a.db')
    cursor = conn.cursor()
    
    # Verify ownership and get trip_id before deleting
    cursor.execute('''
        SELECT Album.trip_id, Trips.user_id 
        FROM Album 
        JOIN Trips ON Album.trip_id = Trips.trip_id 
        WHERE Album.photo_id = ?
    ''', (photo_id,))
    result = cursor.fetchone()
    
    if result is None or result[1] != session['user_id']:
        conn.close()
        return "Photo not found", 404
    
    trip_id = result[0]
    
    # Delete photo
    cursor.execute('DELETE FROM Album WHERE photo_id = ?', (photo_id,))
    conn.commit()
    conn.close()
    
    return redirect(url_for('album', trip_id=trip_id))

# VIEW SPENDING PAGE FOR TRIP
@app.route('/spending/<int:trip_id>')
@login_required
def spending(trip_id):
    # Get trip details and verify ownership
    conn = sqlite3.connect('part_a.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM Trips WHERE trip_id = ? AND user_id = ?', (trip_id, session['user_id']))
    trip = cursor.fetchone()
    conn.close()
    
    if trip is None:
        return "Trip not found", 404
    
    return render_template('spending.html', trip=trip, trip_id=trip_id)

if __name__ == '__main__':
    app.run(debug=True)