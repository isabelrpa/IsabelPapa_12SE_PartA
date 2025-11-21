-- Drop existing tables
DROP TABLE IF EXISTS SpendingLog;
DROP TABLE IF EXISTS Album;
DROP TABLE IF EXISTS Journal;
DROP TABLE IF EXISTS Trips;

-- Trips table
CREATE TABLE IF NOT EXISTS Trips (
    trip_id INTEGER PRIMARY KEY AUTOINCREMENT,
    trip_location TEXT NOT NULL,
    trip_start TEXT NOT NULL,
    trip_end TEXT NOT NULL,
    trip_image TEXT,
    trip_description TEXT,
    rating INTEGER DEFAULT 0 CHECK(rating >= 0 AND rating <= 5)
);

-- Journal table
CREATE TABLE IF NOT EXISTS Journal (
    journal_id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_date TEXT NOT NULL,
    journal_entry TEXT NOT NULL,
    trip_id INTEGER NOT NULL,
    FOREIGN KEY(trip_id) REFERENCES Trips(trip_id) ON DELETE CASCADE
);

-- Album table
CREATE TABLE IF NOT EXISTS Album (
    photo_id INTEGER PRIMARY KEY AUTOINCREMENT,
    photo_path TEXT NOT NULL,
    photo_alt TEXT,
    trip_id INTEGER NOT NULL,
    date_added TEXT NOT NULL,
    FOREIGN KEY(trip_id) REFERENCES Trips(trip_id) ON DELETE CASCADE
);

-- Spending Log table
CREATE TABLE IF NOT EXISTS SpendingLog (
    expense_id INTEGER PRIMARY KEY AUTOINCREMENT,
    expense_date TEXT NOT NULL,
    expense_category TEXT NOT NULL,
    expense_description TEXT,
    amount REAL NOT NULL,
    trip_id INTEGER NOT NULL,
    FOREIGN KEY(trip_id) REFERENCES Trips(trip_id) ON DELETE CASCADE
);

-- Seed Trips data (10+ items)
INSERT INTO Trips (trip_location, trip_start, trip_end, trip_image, trip_description, rating)
VALUES
    ('New York', '2024-12-29', '2025-01-06', 'images/newyork.jpg', 'Winter trip to the Big Apple', 5),
    ('Thailand', '2025-01-02', '2025-01-15', 'images/thailand.jpg', 'Beach paradise and cultural temples', 4),
    ('Singapore', '2023-12-01', '2024-01-11', 'images/singapore.jpg', 'Modern city-state exploration', 5),
    ('Tokyo', '2024-03-15', '2024-03-25', 'images/tokyo.jpg', 'Cherry blossom season', 5),
    ('Paris', '2024-06-10', '2024-06-20', 'images/paris.jpg', 'Romance and culture', 4),
    ('Barcelona', '2024-07-05', '2024-07-15', 'images/barcelona.jpg', 'Gaudi architecture', 4),
    ('Iceland', '2024-09-01', '2024-09-10', 'images/iceland.jpg', 'Northern lights adventure', 5),
    ('Bali', '2024-10-12', '2024-10-22', 'images/bali.jpg', 'Island paradise', 5),
    ('Dubai', '2024-11-05', '2024-11-12', 'images/dubai.jpg', 'Luxury and desert', 3),
    ('Sydney', '2023-11-20', '2023-12-05', 'images/sydney.jpg', 'Harbour and beaches', 4),
    ('Rome', '2024-04-01', '2024-04-10', 'images/rome.jpg', 'Ancient history tour', 5),
    ('London', '2024-08-15', '2024-08-25', 'images/london.jpg', 'British culture immersion', 4);

-- Seed Journal entries
INSERT INTO Journal (entry_date, journal_entry, trip_id)
VALUES
    ('2024-12-30', 'Arrived in New York! Times Square was absolutely incredible at night. The energy here is unlike anything I have experienced before.', 1),
    ('2024-12-31', 'Celebrated New Years Eve in Times Square. Freezing cold but completely worth it. The ball drop was magical!', 1),
    ('2025-01-03', 'Visited the Grand Palace today. The architecture is breathtaking and the golden stupas gleam in the sunlight.', 2),
    ('2025-01-05', 'Beach day at Phuket! Crystal clear water and white sand. Paradise found.', 2),
    ('2023-12-02', 'Marina Bay Sands light show was amazing! The Singapore skyline is futuristic.', 3),
    ('2024-03-16', 'Saw cherry blossoms at Ueno Park. Absolutely magical pink canopy everywhere.', 4),
    ('2024-06-11', 'Climbed the Eiffel Tower today. View was worth the two-hour wait!', 5),
    ('2024-07-06', 'Visited La Sagrada Familia. Gaudi was a genius. Still under construction after 140 years!', 6),
    ('2024-09-02', 'Saw the Northern Lights tonight! Dancing green curtains across the sky. Speechless.', 7),
    ('2024-10-13', 'Temple hopping in Ubud. The rice terraces are stunning.', 8);

-- Seed Album photos
INSERT INTO Album (photo_path, photo_alt, trip_id, date_added)
VALUES
    ('images/statue-liberty.jpg', 'Statue of Liberty at sunset', 1, '2024-12-31'),
    ('images/times-square-night.jpg', 'Times Square lights at night', 1, '2024-12-30'),
    ('images/thai-temple.jpg', 'Ornate Thai temple with gold details', 2, '2025-01-04'),
    ('images/thai-beach.jpg', 'Crystal clear beach in Phuket', 2, '2025-01-06'),
    ('images/merlion.jpg', 'Merlion statue at Marina Bay', 3, '2023-12-03'),
    ('images/cherry-blossoms.jpg', 'Cherry blossom trees in full bloom', 4, '2024-03-17'),
    ('images/eiffel-tower.jpg', 'Eiffel Tower from Trocadero', 5, '2024-06-12'),
    ('images/sagrada-familia.jpg', 'La Sagrada Familia exterior', 6, '2024-07-06'),
    ('images/northern-lights.jpg', 'Green aurora borealis over Iceland', 7, '2024-09-02'),
    ('images/bali-temple.jpg', 'Balinese temple at sunset', 8, '2024-10-14');