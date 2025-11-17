from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from werkzeug.utils import secure_filename
import os
import time

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


# ROUTES

# HOME PAGE (DISPLAY ALL TRIPS)
@app.route('/')
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
    else:
        order_clause = 'ORDER BY trip_id DESC'
    
    # Fetch trips
    query = f'SELECT * FROM Trips {order_clause}'
    cursor.execute(query)
    all_trips = cursor.fetchall()
    conn.close()
    
    return render_template('index.html', trips=all_trips)



# VIEW INDIVIDUAL TRIP DETAILS
@app.route('/trip/<int:trip_id>')
def trip(trip_id):
    # Get trip details
    conn = sqlite3.connect('part_a.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM Trips WHERE trip_id = ?', (trip_id,))
    trip = cursor.fetchone()
    conn.close()
    
    if trip is None:
        return "Trip not found", 404
    
    return render_template('trip.html', trip=trip)



# CREATE (NEW) TRIP
@app.route('/create', methods=['POST', 'GET'])
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

        # Insert into database
        conn = sqlite3.connect('part_a.db')
        cursor = conn.cursor()

        cursor.execute('''
        INSERT INTO Trips (trip_location, trip_start, trip_end, trip_image, trip_description, rating)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (trip_location, trip_start, trip_end, trip_image, trip_description, rating))
        conn.commit()
        conn.close()
        
        return redirect(url_for('index'))
    
    return render_template('form.html')



# UPDATE (EXISTING) TRIP
@app.route('/update/<int:trip_id>', methods=['POST','GET'])
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
            cursor.execute('SELECT trip_image FROM Trips WHERE trip_id = ?', (trip_id,))
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
            WHERE trip_id = ?
        ''', (trip_location, trip_start, trip_end, trip_image, trip_description, rating, trip_id))

        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    
    else:
        # Get existing trip data
        cursor.execute('SELECT * FROM Trips WHERE trip_id = ?', (trip_id,))
        trip = cursor.fetchone()
        conn.close()

        if trip is None:
            return "Trip not found", 404
        
        return render_template('update.html', trip=trip)



# DELETE TRIP
@app.route('/delete/<int:trip_id>')
def delete(trip_id):
    conn = sqlite3.connect('part_a.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM Trips WHERE trip_id=?', (trip_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))



# VIEW JOURNAL ENTRIES FOR TRIP
@app.route('/journal/<int:trip_id>', methods=['GET', 'POST'])
def journal(trip_id):
    conn = sqlite3.connect('part_a.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
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
    elif sort_by == 'id_asc':
        order_clause = 'ORDER BY journal_id ASC'
    elif sort_by == 'id_desc':
        order_clause = 'ORDER BY journal_id DESC'
    else:
        order_clause = 'ORDER BY entry_date DESC'
    
    # Get trip details
    cursor.execute('SELECT * FROM Trips WHERE trip_id = ?', (trip_id,))
    trip = cursor.fetchone()
    
    # Get journal entries with sort
    query = f'SELECT entry_date, journal_entry, journal_id FROM Journal WHERE trip_id = ? {order_clause}'
    cursor.execute(query, (trip_id,))
    entries = cursor.fetchall()
    
    conn.close()

    return render_template('journal.html', entries=entries, trip=trip, trip_id=trip_id)




# CREATE (NEW) JOURNAL ENTRY
@app.route('/journal/add/<int:trip_id>', methods=['GET', 'POST'])
def new_entry(trip_id):
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
def update_journal_entry(entry_id):
    conn = sqlite3.connect('part_a.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
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
        cursor.execute('SELECT trip_id FROM Journal WHERE journal_id = ?', (entry_id,))
        result = cursor.fetchone()
        trip_id = result['trip_id']
        
        return redirect(url_for('journal', trip_id=trip_id))
    
    else:
        # GET request - render form (keep this for fallback)
        cursor.execute('SELECT * FROM Journal WHERE journal_id = ?', (entry_id,))
        entry = cursor.fetchone()
        conn.close()
        
        if entry is None:
            return "Journal entry not found", 404
        
        return render_template('update_journal_entry.html', entry=entry)



# DELETE JOURNAL ENTRY
@app.route('/journal/delete/<int:entry_id>')
def delete_journal_entry(entry_id):
    conn = sqlite3.connect('part_a.db')
    cursor = conn.cursor()
    
    # Get trip_id before deleting
    cursor.execute('SELECT trip_id FROM Journal WHERE journal_id = ?', (entry_id,))
    result = cursor.fetchone()
    trip_id = result[0]
    
    # Delete entry
    cursor.execute('DELETE FROM Journal WHERE journal_id = ?', (entry_id,))
    conn.commit()
    conn.close()
    
    return redirect(url_for('journal', trip_id=trip_id))



# VIEW PHOTO ALBUM FOR TRIP
@app.route('/album/<int:trip_id>')
def album(trip_id):
    conn = sqlite3.connect('part_a.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get trip details
    cursor.execute('SELECT * FROM Trips WHERE trip_id = ?', (trip_id,))
    trip = cursor.fetchone()
    
    # Get ALL photos for this trip, ordered by most recent first (NO LIMIT)
    cursor.execute('''
        SELECT * FROM Album 
        WHERE trip_id = ? 
        ORDER BY date_added DESC
    ''', (trip_id,))
    photos = cursor.fetchall()
    
    conn.close()
    
    if trip is None:
        return "Trip not found", 404
    
    return render_template('album.html', trip=trip, trip_id=trip_id, photos=photos)


# UPLOAD PHOTO TO ALBUM
@app.route('/album/<int:trip_id>/upload', methods=['POST'])
def upload_photo(trip_id):
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
def update_photo(photo_id):
    conn = sqlite3.connect('part_a.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
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
            
            # Get trip_id for redirect
            cursor.execute('SELECT trip_id FROM Album WHERE photo_id = ?', (photo_id,))
            result = cursor.fetchone()
            trip_id = result['trip_id']
            conn.close()
            
            return redirect(url_for('album', trip_id=trip_id))
        else:
            conn.close()
            return "Invalid file type. Please upload PNG, JPG, JPEG, GIF, or WEBP", 400
    
    else:
        # Get existing photo data
        cursor.execute('SELECT * FROM Album WHERE photo_id = ?', (photo_id,))
        photo = cursor.fetchone()
        conn.close()
        
        if photo is None:
            return "Photo not found", 404
        
        return render_template('update_photo.html', photo=photo)


# DELETE PHOTO FROM ALBUM
@app.route('/album/delete/<int:photo_id>')
def delete_photo(photo_id):
    conn = sqlite3.connect('part_a.db')
    cursor = conn.cursor()
    
    # Get trip_id before deleting
    cursor.execute('SELECT trip_id FROM Album WHERE photo_id = ?', (photo_id,))
    result = cursor.fetchone()
    trip_id = result[0]
    
    # Delete photo
    cursor.execute('DELETE FROM Album WHERE photo_id = ?', (photo_id,))
    conn.commit()
    conn.close()
    
    return redirect(url_for('album', trip_id=trip_id))

# VIEW SPENDING PAGE FOR TRIP
@app.route('/spending/<int:trip_id>')
def spending(trip_id):

    # Get trip details
    conn = sqlite3.connect('part_a.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM Trips WHERE trip_id = ?', (trip_id,))
    trip = cursor.fetchone()
    conn.close()
    
    if trip is None:
        return "Trip not found", 404
    
    return render_template('spending.html', trip=trip, trip_id=trip_id)

if __name__ == '__main__':
    app.run(debug=True)
    