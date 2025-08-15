from flask import Flask, render_template, request, redirect, url_for, session, jsonify, g, flash
import mysql.connector
import base64
import os
import pygame.mixer
from io import BytesIO
from random import randint

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Securely generating a secret key

# Initialize Pygame Mixer
pygame.mixer.init()

def get_db():
    if 'db' not in g:
        g.db = mysql.connector.connect(
            host='localhost',
            user='root',
            password='shreju@2004',
            database='music_player'  # Replace with your actual database name
        )
    return g.db

@app.before_request
def before_request():
    g.db = get_db()
    g.cur = g.db.cursor(dictionary=True)

@app.teardown_request
def teardown_request(exception):
    cur = g.pop('cur', None)
    db = g.pop('db', None)
    if cur is not None:
        cur.close()
    if db is not None:
        db.close()

@app.route('/')
def index():
    return render_template('rafi.html')

@app.route('/show_login')
def show_login():
    return render_template('login_page.html')



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')  # Safer than ['email']
        password = request.form.get('password')

        try:
            g.cur.execute("SELECT * FROM user_data WHERE email_id = %s AND user_password = %s", (email, password))
            user = g.cur.fetchone()

            if user:
                session['email_id'] = user['email_id']
                return redirect(url_for('change_background'))
            else:
                return "Login failed. Please check your credentials."
        except mysql.connector.Error as e:
            print("Error occurred while executing SQL query:", e)
            return "An error occurred during login."

    # Handle GET request: just show the login form
    return render_template('login_page.html')


@app.route('/register', methods=['POST'])
def register():
    first_name = request.form.get('firstname')
    last_name = request.form.get('lastname')
    email_id = request.form.get('email')
    password = request.form.get('password')
    
    special_char = ['@', '#', '$', '%', '^', '&', '*', '(', ')', '{', '}', '[', ']']
    number = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0']
    alphanumeric = list('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz')

    if not ("@gmail.com" in email_id):
        flash("Please enter a full email address.")
        return redirect(url_for('register_page'))  # Assuming you have a register_page route
    if not any(char in special_char for char in password):
        flash("Password must contain at least one special character.")
        return redirect(url_for('register_page'))
    if not any(char in number for char in password):
        flash("Password must contain at least one number.")
        return redirect(url_for('register_page'))
    if not any(char in alphanumeric for char in password):
        flash("Password must contain at least one alphanumeric character.")
        return redirect(url_for('register_page'))
    
    try:
        g.cur.execute("INSERT INTO user_data (First_name, Last_name, user_password, email_id) VALUES (%s, %s, %s, %s)", 
                      (first_name, last_name, password, email_id))
        g.db.commit()
        flash("Registration successful!")
        return redirect(url_for('index'))  # Redirect to the index after successful registration
    except mysql.connector.Error as e:
        flash(f"Error occurred during registration: {e}")
        return redirect(url_for('register'))
# Example route to display the registration form
@app.route('/register_page')
def register_page():
    return render_template('login_page.html')  # Assuming you have a register.html template
@app.route('/change_background')
def change_background():
    if 'email_id' in session:
        return redirect(url_for('display_all_playlists'))
    else:
        return redirect(url_for('index'))

@app.route('/button_click', methods=['POST'])
def button_click():
    try:
        button_id = request.json.get('button_id')
        
        # Example: Insert the song identified by button_id into your database
        # Replace this with your actual database insertion logic
        g.cur.execute("INSERT INTO your_table (button_id) VALUES (%s)", (button_id,))
        g.db.commit()
        
        return jsonify({'status': 'success', 'button_id': button_id})
    except mysql.connector.Error as e:
        print("Error occurred while inserting song:", e)
        return jsonify({'error': str(e)}), 500

def fetch_image_from_db(img_id):
    try:
        g.cur.execute("SELECT image_data FROM images WHERE id = %s", (img_id,))
        result = g.cur.fetchone()
        
        if result is None:
            print(f"No image found with id: {img_id}")
            return None

        return result['image_data']  # Fetch the 'image_data' column
    except Exception as e:
        print("Error fetching image:", e)
        return None

@app.route('/get_song_id')
def get_song_id():
    song_name = request.args.get('song_name')
    try:
        # Log the song_name to ensure it's being received correctly
        print(f"Fetching ID for song name: {song_name}")

        # Fetch song ID from the database
        g.cur.execute("SELECT id FROM images WHERE song_name = %s", (song_name,))
        song = g.cur.fetchone()

        if song:
            # Redirect to the get_data route with the song ID
            return redirect(url_for('get_data', id=song['id']))
        else:
            return f"No data found for song name: {song_name}", 404
    except mysql.connector.Error as e:
        print("Error fetching song ID:", e)
        return "An error occurred while fetching the song ID."



@app.route('/get_data')
def get_data():
    img_id = request.args.get('id')
    try:
        g.cur.execute("SELECT image_data, song_name, BPM, scale, Genre, lyrics FROM images WHERE id = %s", (img_id,))
        data = g.cur.fetchone()

        if data is None:
            print(f"No data found with id: {img_id}")
            return jsonify({'error': 'No data found'}), 404

        image_data = base64.b64encode(data['image_data']).decode('utf-8')
        song_name = data['song_name']
        bpm = data['BPM']
        scale = data['scale']
        genre = data['Genre']
        lyrics = data['lyrics']

        # Insert audio data into 'songs' table (if not already present)
        try:
            # Check if song already exists
            g.cur.execute("SELECT COUNT(*) AS count FROM songs WHERE s_id = %s", (img_id,))
            if g.cur.fetchone()['count'] == 0:
                g.cur.execute("INSERT INTO songs (s_id, audio) VALUES (%s, %s)", (img_id, b'your_audio_blob_data_here'))
                g.db.commit()
                print(f"Inserted audio for s_id={img_id} into 'songs' table")
            else:
                print(f"Audio for s_id={img_id} already exists in 'songs' table")
        except mysql.connector.Error as e:
            print("Error inserting data into 'songs' table:", e)

        return render_template('track_page.html', image_data=image_data, song_name=song_name,
                               bpm=bpm, scale=scale, genre=genre, lyrics=lyrics)
                                
    except mysql.connector.Error as e:
        print("Error occurred while fetching data:", e)
        return jsonify({'error': str(e)}), 500


@app.route('/get_background_image', methods=['POST'])
def get_background_image():
    img_id = request.json.get('img_id')
    image_data = fetch_image_from_db(img_id)
    
    if image_data:
        # Encode image data to base64
        encoded_image = base64.b64encode(image_data).decode('utf-8')
        return jsonify({'image_data': encoded_image})
    else:
        return jsonify({'error': 'Image not found'}), 404

@app.route('/get_additional_data')
def get_additional_data():
    song_id = request.args.get('id')

    try:
        # Check if the user is logged in
        if 'email' not in session:
            return redirect(url_for('login'))

        email_id = session['email']

        # Retrieve audio data from the database
        g.cur.execute("SELECT audio FROM songs WHERE s_id = %s", (song_id,))
        audio_data = g.cur.fetchone()

        # Check if audio data is None (meaning the song was not found)
        if not audio_data:
            return jsonify({'error': 'Audio data not found'}), 404

        audio_data_b64 = base64.b64encode(audio_data['audio']).decode('utf-8')

        return jsonify({'status': 'success', 'audio_data': audio_data_b64})

    except mysql.connector.Error as e:
        print("Error occurred while executing SQL query:", e)
        return jsonify({'error': str(e)}), 500

@app.route('/logout')
def logout():
    session.pop('email_id', None)
    return redirect(url_for('index'))

@app.route('/playlist')
def playlist():
    return render_template('playlist.html')

@app.route('/show_play')
def show_play():
    try:
        g.cur.execute("SELECT pl_id, playlist_name FROM playlist")
        playlists = g.cur.fetchall()
        return render_template('show_play.html', playlists=playlists)
    except mysql.connector.Error as e:
        print("Error fetching playlists:", e)
        return jsonify({'error': str(e)}), 500


@app.route('/getnewpage2')
def getnewpage2():
    return render_template('show_play.html')

@app.route('/get_songs', methods=['POST'])
def get_songs():
    playlist_id = request.form['button_id']
    try:
        query = """
            SELECT s.s_id, s.song_name AS title, i.album_name AS album, s.duration, i.image_data 
            FROM songs s 
            JOIN images i ON s.playlist_id = i.id 
            WHERE s.playlist_id = %s
        """
        g.cur.execute(query, (playlist_id,))
        songs = g.cur.fetchall()
        for song in songs:
            song['image_url'] = 'data:image/jpeg;base64,' + base64.b64encode(song['image_data']).decode('utf-8')
            del song['image_data']  # Remove raw image data from response
        
        return render_template('songs.html', songs=songs)  # Render the songs template with songs data
    except mysql.connector.Error as e:
        print("Error occurred while fetching songs:", e)
        return jsonify({'error': str(e)}), 500

@app.route('/show_play/<playlist_name>')
def show_playlist(playlist_name):
    try:
        # Construct the SQL query dynamically based on the playlist_name
        query = f"SELECT song_name FROM `{playlist_name}`"
        g.cur.execute(query)
        songs = g.cur.fetchall()

        return render_template('display_playlist_song.html', playlist_name=playlist_name, songs=songs)
    except mysql.connector.Error as e:
        print(f"Error fetching playlist {playlist_name}:", e)
        return jsonify({'error': str(e)}), 500



@app.route('/simple')
def display_all_playlists():
    if 'email_id' not in session:
        return redirect(url_for('login'))  # Redirect to login if user is not logged in
    
    email_id = session['email_id']
    
    try:
        g.cur.execute("SELECT playlist_name FROM playlist WHERE user_name = %s", (email_id,))
        playlists = g.cur.fetchall()
        return render_template('simple.html', playlists=playlists)
    except mysql.connector.Error as e:
        print("Error fetching playlists:", e)
        return jsonify({'error': str(e)}), 500


@app.route('/insert_data', methods=['POST'])
def insert_data():
    try:
        a = randint(1, 10000)  # Use a larger range to reduce the chance of duplicate IDs
        name = request.form.get('playlist_name')
        user_name = session.get('email_id')
        
        # Insert the new playlist into the playlist table
        g.cur.execute("INSERT INTO playlist (pl_id, playlist_name, user_name) VALUES (%s, %s, %s)", (a, name, user_name))
        g.db.commit()
        
        # Define the name of the new table (e.g., using the playlist id or name)
        new_table_name = f"`{name}`"
        
        # Define the schema for the new table
        create_table_query = f"""
            CREATE TABLE IF NOT EXISTS {new_table_name} (
                id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                song_name VARCHAR(50)
            );
        """
        
        # Create the new table with the defined schema
        g.cur.execute(create_table_query)
        g.db.commit()
        
        return redirect(url_for('display_all_playlists'))
    except mysql.connector.Error as e:
        print("Error occurred while inserting data or creating table:", e)
        return jsonify({'error': str(e)}), 500


@app.route('/add_user_defined_playlist')
def add_user_defined_playlist():
    return render_template('add_user_defined_playlist.html')

@app.route('/show_user_playlist/<playlist_name>')
def show_user_playlist(playlist_name):
    try:
        # Construct the SQL query dynamically based on the playlist_name
        query = f"SELECT song_name FROM `{playlist_name}`"
        g.cur.execute(query)
        songs = g.cur.fetchall()

        return render_template('show_playlist.html', playlist_name=playlist_name, songs=songs)
    except mysql.connector.Error as e:
        print(f"Error fetching playlist {playlist_name}:", e)
        return jsonify({'error': str(e)}), 500

@app.route('/rafi')
def rafi():
    return render_template('rafi.html')


@app.route('/user_profile')
def about_us():
    return render_template('user_profile.html')

@app.route('/create_custom_table', methods=['POST'])
def create_custom_table():
    table_name = request.form.get('table_name')
    print(f"Creating table with name: {table_name}")
    try:
        create_table_query = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                song_id INT,
                song_name VARCHAR(255)
            );
        """
        g.cur.execute(create_table_query)
        g.db.commit()
        return jsonify({'status': 'success', 'message': f'Table "{table_name}" created successfully.'})
    except mysql.connector.Error as e:
        print("Error creating table:", e)
        return jsonify({'status': 'error', 'error': str(e)}), 500



@app.route('/add_song_to_playlist', methods=['POST'])
def add_song_to_playlist():
    song_name = request.form.get('song_name')
    playlist_name = request.form.get('playlist_name')

    print(f"Adding song with name: {song_name} to playlist: {playlist_name}")

    if not song_name or not playlist_name:
        return jsonify({'status': 'error', 'error': 'Missing song name or playlist name'}), 400

    try:
        # Check if the song exists in the images table
        g.cur.execute("SELECT COUNT(*) AS count FROM images WHERE song_name = %s", (song_name,))
        song_exists = g.cur.fetchone()['count'] > 0

        if not song_exists:
            return jsonify({'status': 'error', 'error': 'Image not available for the song.'}), 400

        # Check if the song already exists in the playlist
        g.cur.execute(f"SELECT COUNT(*) AS count FROM {playlist_name} WHERE song_name = %s", (song_name,))
        count = g.cur.fetchone()['count']

        if count > 0:
            return jsonify({'status': 'error', 'error': 'Song already exists in the playlist.'}), 400

        # Insert the song into the specified playlist table
        g.cur.execute(f"INSERT INTO {playlist_name} (song_name) VALUES (%s)", (song_name,))
        g.db.commit()

        return jsonify({'status': 'success', 'message': f'Song "{song_name}" added to playlist {playlist_name}.'})
    except mysql.connector.Error as e:
        print("Error adding song:", e)
        return jsonify({'status': 'error', 'error': str(e)}), 500




@app.after_request
def add_header(response):
    response.cache_control.no_store = True
    return response

@app.route('/user_profile')
def user_profile():
    if 'email' not in session:
        return redirect(url_for('login'))

    user_email = session['email']
    song_id = request.args.get(id)
    g.cur.execute("select song_name from images where s_id = %s",(song_id,))
    print("song_id = \n\n\n\n\n{song_id}\n\n\n\n\n\n")
    
@app.route('/playlists')
def playlists():
    # Check if user is logged in
    if 'email' not in session:
        return redirect(url_for('login'))

    user_email = session['email']

    # Connect to the database
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)

    # Fetch playlists for the logged-in user
    query = "SELECT playlist_name FROM playlist WHERE user_name = %s"
    cursor.execute(query, (user_email,))
    playlists = cursor.fetchall()

    # Close the database connection
    cursor.close()
    connection.close()

    return render_template('playlists.html', playlists=playlists)



@app.route('/search', methods=['GET', 'POST'])
def search():
    search_results = []
    if request.method == 'POST':
        connection = get_db()
        cursor = connection.cursor(dictionary=True)
        search_query = request.form['search']
        
        query = "SELECT * FROM images WHERE song_name LIKE %s"
        cursor.execute(query, (f"%{search_query}%",))
        search_results = cursor.fetchall()
        
        cursor.close()

    return render_template('search.html', search_results=search_results)
    
    
    
@app.route('/king_playlist')
def artist_play():
    return render_template('king_playlist.html')

@app.route('/MC_stan_play')
def artist_play1():
    return render_template('MC_stan_play.html')



@app.route('/YNG_DADDY_X_LIL_SLATT')
def artist_page2():
    return render_template('YNG_DADDY_X_LIL_SLATT .html')

if __name__ == '__main__':
        app.run(debug=True)
    