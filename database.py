import sqlite3
import os
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
def init_database():
    """
    Inisialisasi database SIS dengan skema lengkap dan DUMMY DATA YANG KAYA
    biar pas di-screenshot terlihat bagus dan profesional.
    """
    DB_FILE = 'sis.db'
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        print(f"🗑️  Database lama '{DB_FILE}' dihapus...")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    print("📦 Membuat tabel-tabel database...")
    cursor.executescript('''
        CREATE TABLE User (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('admin', 'pengajar', 'siswa'))
        );
        CREATE TABLE Sekolah (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kode_sekolah TEXT UNIQUE NOT NULL,
            nama_sekolah TEXT NOT NULL,
            alamat TEXT,
            jenis_sekolah TEXT NOT NULL
        );
        CREATE TABLE Pengajar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kode_pengajar TEXT UNIQUE NOT NULL,
            nama_pengajar TEXT NOT NULL,
            program TEXT NOT NULL,
            user_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES User(id)
        );
        CREATE TABLE Siswa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama_siswa TEXT NOT NULL,
            kelas_tingkat TEXT NOT NULL,
            program TEXT NOT NULL,
            sekolah_id INTEGER,
            user_id INTEGER,
            FOREIGN KEY (sekolah_id) REFERENCES Sekolah(id),
            FOREIGN KEY (user_id) REFERENCES User(id)
        );
        CREATE TABLE Program (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama_program TEXT NOT NULL
        );
        CREATE TABLE Kelas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kode_kelas TEXT NOT NULL UNIQUE,
            nama_kelas TEXT NOT NULL,
            program_id INTEGER,
            sekolah_id INTEGER,
            pengajar_id INTEGER,
            waktu_mulai TEXT NOT NULL,
            waktu_akhir TEXT NOT NULL,
            hari TEXT NOT NULL,
            tanggal_mulai TEXT NOT NULL,
            FOREIGN KEY (program_id) REFERENCES Program(id),
            FOREIGN KEY (sekolah_id) REFERENCES Sekolah(id),
            FOREIGN KEY (pengajar_id) REFERENCES Pengajar(id)
        );
        CREATE TABLE KelasSiswa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kelas_id INTEGER,
            siswa_id INTEGER,
            FOREIGN KEY (kelas_id) REFERENCES Kelas(id),
            FOREIGN KEY (siswa_id) REFERENCES Siswa(id),
            UNIQUE(kelas_id, siswa_id)
        );
        CREATE TABLE Materi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            program TEXT NOT NULL,
            pertemuan_ke INTEGER NOT NULL,
            detail_materi TEXT NOT NULL
        );
        CREATE TABLE AbsensiSesi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kelas_id INTEGER,
            tanggal TEXT NOT NULL,
            pengajar_id INTEGER,
            pengajar_pengganti_id INTEGER,
            foto_selfie TEXT NOT NULL,
            materi_pembelajaran TEXT,
            capaian_pembelajaran TEXT,
            FOREIGN KEY (kelas_id) REFERENCES Kelas(id),
            FOREIGN KEY (pengajar_id) REFERENCES Pengajar(id),
            FOREIGN KEY (pengajar_pengganti_id) REFERENCES Pengajar(id)
        );
        CREATE TABLE AbsensiSiswa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sesi_id INTEGER,
            siswa_id INTEGER,
            kehadiran_mutu TEXT,
            kehadiran TEXT,
            kedisiplinan_mutu TEXT,
            kedisiplinan TEXT,
            materi_kreativitas_mutu TEXT,
            materi_kreativitas TEXT,
            kerjasama_mutu TEXT,
            kerjasama TEXT,
            FOREIGN KEY (sesi_id) REFERENCES AbsensiSesi(id),
            FOREIGN KEY (siswa_id) REFERENCES Siswa(id)
        );
        CREATE TABLE Gaji (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pengajar_id INTEGER NOT NULL,
            periode TEXT NOT NULL, -- Format: YYYY-MM
            transport_pengajaran INTEGER,
            tunjangan_marketing INTEGER,
            tunjangan_tugas_tambahan INTEGER,
            tunjangan_lain_lain INTEGER,
            total_gaji INTEGER,
            tanggal_dibuat TEXT NOT NULL,
            FOREIGN KEY (pengajar_id) REFERENCES Pengajar(id)
        );
        CREATE TABLE PasswordResetTokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            token TEXT NOT NULL,
            expires_at DATETIME NOT NULL,
            used BOOLEAN DEFAULT FALSE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES User(id)
        );
    ''')
    print("🌱 Mengisi Data Dummy...")
    users = [
        ('admin', generate_password_hash('admin123'), 'admin'),
        ('iwan', generate_password_hash('teacher123'), 'pengajar'),
        ('adit', generate_password_hash('teacher123'), 'pengajar'),
        ('anung', generate_password_hash('teacher123'), 'pengajar'),
    ]
    cursor.executemany("INSERT INTO User (username, password, role) VALUES (?, ?, ?)", users)
    schools = [
        ('S-FI', 'SD Fitrah Insani', 'Jl. Langkapura No. 10', 'Muslim'), 
        ('S-XA', 'SD Xaverius 1', 'Jl. Pahoman No. 5', 'Non Muslim'),
        ('S-AZ', 'SD Al Azhar 50', 'Jl. Rajabasa', 'Muslim'),
        ('S-PB', 'SD Pelita Bangsa', 'Jl. Antasari', 'Non Muslim')
    ]
    cursor.executemany("INSERT INTO Sekolah (kode_sekolah, nama_sekolah, alamat, jenis_sekolah) VALUES (?, ?, ?, ?)", schools)
    programs = [('Robotik',), ('Bahasa Inggris',), ('Desain Grafis',), ('Coding for Kids',)]
    cursor.executemany("INSERT INTO Program (nama_program) VALUES (?)", programs)
    teachers = [
        ('P-RB01', 'Dr. Iwan Purwanto, S.Kom, MTI', 'Robotik', 2),
        ('P-EN01', 'Adhitya Barkah, M.M.', 'Bahasa Inggris', 3),
        ('P-DG01', 'Anung B. Ariwibowo, M.Kom', 'Desain Grafis', 4)
    ]
    cursor.executemany("INSERT INTO Pengajar (kode_pengajar, nama_pengajar, program, user_id) VALUES (?, ?, ?, ?)", teachers)
    siswa_data = [
        ('Dewanto', '4 SD', 'Robotik', 1), ('Felix', '5 SD', 'Robotik', 2),
        ('Rayyan', '4 SD', 'Robotik', 1), ('Imam', '5 SD', 'Bahasa Inggris', 3),
        ('Bayu', '5 SD', 'Bahasa Inggris', 3), ('Vira', '4 SD', 'Bahasa Inggris', 4),
        ('Bambang', '4 SD', 'Bahasa Inggris', 2), ('Faiz', '5 SD', 'Desain Grafis', 1),
        ('Rombon', '5 SD', 'Desain Grafis', 4), ('Sarah', '4 SD', 'Desain Grafis', 3),
        ('Kevin', '6 SD', 'Robotik', 2), ('Nadia', '3 SD', 'Desain Grafis', 1),
        ('Rizky', '5 SD', 'Coding for Kids', 3), ('Putri', '4 SD', 'Coding for Kids', 4),
        ('Dimas', '6 SD', 'Robotik', 1)
    ]
    for i, (nama, kelas, prog, sek_id) in enumerate(siswa_data):
        username = nama.lower()
        password = generate_password_hash('student123')
        cursor.execute("INSERT INTO User (username, password, role) VALUES (?, ?, ?)", (username, password, 'siswa'))
        user_id = cursor.lastrowid
        cursor.execute("INSERT INTO Siswa (nama_siswa, kelas_tingkat, program, sekolah_id, user_id) VALUES (?, ?, ?, ?, ?)", 
                       (nama, kelas, prog, sek_id, user_id))
    today = datetime.now()
    start_date = (today - timedelta(days=30)).strftime('%Y-%m-%d')
    classes = [
        ('K-ROB-A', 'Robotik - SD Fitrah Insani', 1, 1, 1, '08:00', '09:30', 'Senin', start_date),
        ('K-ENG-B', 'English Club - Xaverius', 2, 2, 2, '10:00', '11:30', 'Selasa', start_date),
        ('K-DSG-C', 'Desain Grafis - Al Azhar', 3, 3, 3, '13:00', '14:30', 'Rabu', start_date),
        ('K-COD-D', 'Coding Kids - Pelita', 4, 4, 1, '15:00', '16:30', 'Kamis', start_date)
    ]
    cursor.executemany('''INSERT INTO Kelas (kode_kelas, nama_kelas, program_id, sekolah_id, pengajar_id, waktu_mulai, waktu_akhir, hari, tanggal_mulai) 
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', classes)
    enrollments = [
        (1, 1), (1, 2), (1, 3), (1, 11), (1, 15),
        (2, 4), (2, 5), (2, 6), (2, 7),
        (3, 8), (3, 9), (3, 10), (3, 12),
        (4, 13), (4, 14)
    ]
    cursor.executemany("INSERT INTO KelasSiswa (kelas_id, siswa_id) VALUES (?, ?)", enrollments)
    materi = [
        ('Robotik', 1, 'Pengenalan Komponen & Safety'),
        ('Robotik', 2, 'Merakit Robot Sederhana (Line Follower)'),
        ('Robotik', 3, 'Logika Pemrograman Dasar'),
        ('Bahasa Inggris', 1, 'Introduction & Greetings'),
        ('Bahasa Inggris', 2, 'Daily Activities'),
        ('Desain Grafis', 1, 'Pengenalan CorelDraw / Canva'),
        ('Desain Grafis', 2, 'Teori Warna & Tipografi')
    ]
    cursor.executemany("INSERT INTO Materi (program, pertemuan_ke, detail_materi) VALUES (?, ?, ?)", materi)
    tgl_sesi_1 = (today - timedelta(days=14)).strftime('%Y-%m-%d')
    tgl_sesi_2 = (today - timedelta(days=7)).strftime('%Y-%m-%d')
    tgl_sesi_3 = today.strftime('%Y-%m-%d')
    sesi_data = [
        (1, tgl_sesi_1, 1, 'selfie_dummy_1.jpg', 'Pengenalan Komponen', 'Siswa paham jenis sensor'),
        (1, tgl_sesi_2, 1, 'selfie_dummy_2.jpg', 'Merakit Robot', 'Robot berhasil berjalan'),
        (1, tgl_sesi_3, 1, 'selfie_dummy_3.jpg', 'Logika Dasar', 'Siswa bisa coding loop')
    ]
    cursor.executemany('''INSERT INTO AbsensiSesi (kelas_id, tanggal, pengajar_id, foto_selfie, materi_pembelajaran, capaian_pembelajaran) 
                          VALUES (?, ?, ?, ?, ?, ?)''', sesi_data)
    sesi_ids = [1, 2, 3]
    siswa_robotik = [1, 2, 3, 11, 15]
    for s_id in sesi_ids:
        for siswa_id in siswa_robotik:
            hadir = 'Hadir'
            mutu = 'A'
            if s_id == 2 and siswa_id == 2:
                hadir = 'Sakit'
                mutu = 'C'
            cursor.execute('''INSERT INTO AbsensiSiswa 
                (sesi_id, siswa_id, kehadiran, kehadiran_mutu, kedisiplinan, kedisiplinan_mutu, 
                 materi_kreativitas, materi_kreativitas_mutu, kerjasama, kerjasama_mutu)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                (s_id, siswa_id, 
                 f"Siswa {hadir}", mutu, 
                 "Sangat Baik", "A", 
                 "Kreatif", "A", 
                 "Aktif", "B"))
    bulan_lalu = (today - timedelta(days=30)).strftime('%Y-%m')
    cursor.execute('''INSERT INTO Gaji 
        (pengajar_id, periode, transport_pengajaran, tunjangan_marketing, tunjangan_tugas_tambahan, tunjangan_lain_lain, total_gaji, tanggal_dibuat)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        (1, bulan_lalu, 1500000, 200000, 500000, 0, 2200000, today.strftime('%Y-%m-%d')))
    conn.commit()
    conn.close()
    print("\n✅ Database berhasil di-reset dengan data dummy!")
    print("🔑 KREDENSIAL LOGIN:")
    print("   -------------------------------------------------")
    print("   👨‍💼 ADMIN    : admin / admin123")
    print("   👨‍🏫 PENGAJAR : iwan / teacher123")
    print("   👨‍🎓 SISWA    : dewanto / student123")
    print("   -------------------------------------------------")
if __name__ == '__main__':
    init_database()
