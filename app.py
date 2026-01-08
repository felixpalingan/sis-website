import os
import secrets
from flask import Flask, render_template, request, redirect, url_for, session, flash, g, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sqlite3
from datetime import datetime, timedelta
import csv
import io
PENILAIAN_MAP = {
    'kehadiran': {
        'A': 'ananda menunjukkan komitmen yang tinggi dengan kehadiran yang konsisten dalam setiap sesi, selalu datang tepat waktu dan siap untuk belajar.',
        'B': 'ananda menunjukkan komitmen yang cukup baik dalam kehadiran, meski beberapa kali absen/terlambat, antusiasme dan partisipasinya sangat positif.',
        'C': 'kehadiran ananda perlu ditingkatkan untuk dapat mengikuti perkembangan materi secara maksimal. Siswa dianggap tidak hadir pada sesi ini.'
    },
    'kedisiplinan': {
        'A': 'ananda menunjukkan kedisiplinan yang sangat baik dengan selalu mematuhi aturan, mengikuti instruksi dengan tepat, dan menjaga kerapihan dalam setiap kegiatan.',
        'B': 'ananda menunjukkan kedisiplinan yang cukup baik dalam mengikuti kegiatan, dengan konsisten hadir tepat waktu dan mematuhi instruksi.',
        'C': 'ananda perlu meningkatkan kedisiplinan dalam mematuhi aturan dan mengikuti instruksi agar kegiatan berjalan lebih lancar.'
    },
    'materi_kreativitas': {
        'A': 'ananda menunjukkan kreativitas yang luar biasa dengan menghasilkan ide-ide inovatif dan solusi unik saat merancang serta membangun robot.',
        'B': 'ananda menunjukkan pemahaman yang mendalam terhadap materi dan mampu menciptakan solusi kreatif dalam setiap proyek yang dikerjakannya.',
        'C': 'ananda perlu lebih aktif dalam mencoba ide-ide baru dan eksplorasi materi untuk meningkatkan kreativitasnya.'
    },
    'kerjasama': {
        'A': 'ananda menunjukkan kerjasama yang luar biasa, saling membantu dan menghargai ide teman-teman, sehingga berhasil menyelesaikan tugas bersama dengan baik.',
        'B': 'ananda mampu bekerjasama dengan baik dalam kelompok dan berkontribusi secara positif dalam tugas bersama.',
        'C': 'ananda perlu lebih aktif berkomunikasi dan berkolaborasi dengan anggota kelompok lainnya untuk mencapai tujuan bersama.'
    }
}
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "kunci-rahasia-yang-sangat-aman")
DATABASE = 'sis.db'
app.jinja_env.globals['datetime'] = datetime
def get_db():
    """Membuka koneksi baru ke database jika belum ada untuk request saat ini."""
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
    return g.db
@app.teardown_appcontext
def close_db(e=None):
    """Menutup koneksi database di akhir request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()
def login_required(f):
    """Decorator untuk memastikan pengguna sudah login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function
def role_required(role):
    """Decorator untuk memastikan pengguna memiliki peran tertentu."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            db = get_db()
            user = db.execute('SELECT role FROM User WHERE id = ?', (session['user_id'],)).fetchone()
            if not user or user['role'] != role:
                flash('Akses ditolak. Anda tidak memiliki izin.', 'error')
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    user = db.execute('SELECT role FROM User WHERE id = ?', (session['user_id'],)).fetchone()
    if user['role'] == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif user['role'] == 'pengajar':
        return redirect(url_for('teacher_dashboard'))
    elif user['role'] == 'siswa':
        return redirect(url_for('student_portfolio'))
    return redirect(url_for('login'))
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        user = db.execute('SELECT * FROM User WHERE username = ?', (username,)).fetchone()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('index'))
        else:
            flash('Username atau password salah', 'error')
    return render_template('login.html')
@app.route('/logout')
def logout():
    session.clear()
    flash('Anda berhasil logout', 'success')
    return redirect(url_for('login'))
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    return "Forgot Password feature is available."
@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    return f"Reset Password feature for token {token} is available."
@app.route('/admin/dashboard')
@role_required('admin')
def admin_dashboard():
    db = get_db()
    classes = db.execute('''
        SELECT 
            k.id, 
            k.kode_kelas, 
            k.nama_kelas, 
            pg.program as nama_program,
            pg.nama_pengajar, 
            COUNT(ks.siswa_id) as jumlah_siswa
        FROM Kelas k
        LEFT JOIN Pengajar pg ON k.pengajar_id = pg.id
        LEFT JOIN KelasSiswa ks ON k.id = ks.kelas_id
        GROUP BY k.id
        ORDER BY k.nama_kelas
    ''').fetchall()
    return render_template('admin_dashboard.html', classes=classes)
@app.route('/admin/data/<tipe>')
@role_required('admin')
def admin_manage_data(tipe):
    db = get_db()
    if tipe == 'sekolah':
        data = db.execute('SELECT * FROM Sekolah ORDER BY nama_sekolah').fetchall()
        columns = ['ID', 'Kode', 'Nama Sekolah', 'Alamat', 'Jenis']
    elif tipe == 'pengajar':
        data = db.execute('''
            SELECT p.id, p.kode_pengajar, p.nama_pengajar, p.program, u.username 
            FROM Pengajar p 
            LEFT JOIN User u ON p.user_id = u.id 
            ORDER BY p.nama_pengajar
        ''').fetchall()
        columns = ['ID', 'Kode', 'Nama Pengajar', 'Program', 'Username']
    elif tipe == 'program':
        data = db.execute('SELECT * FROM Program ORDER BY nama_program').fetchall()
        columns = ['ID', 'Nama Program']
    elif tipe == 'siswa':
        data = db.execute('''
            SELECT s.id, s.nama_siswa, s.kelas_tingkat, s.program, sk.nama_sekolah, u.username 
            FROM Siswa s 
            LEFT JOIN Sekolah sk ON s.sekolah_id = sk.id 
            LEFT JOIN User u ON s.user_id = u.id 
            ORDER BY s.nama_siswa
        ''').fetchall()
        columns = ['ID', 'Nama Siswa', 'Tingkat', 'Program', 'Sekolah', 'Username']
    else:
        flash('Tipe data tidak valid', 'error')
        return redirect(url_for('admin_dashboard'))
    return render_template('admin_manage_data.html', data=data, columns=columns, tipe=tipe)
@app.route('/admin/input-sekolah', methods=['GET', 'POST'])
@role_required('admin')
def input_sekolah():
    if request.method == 'POST':
        db = get_db()
        db.execute(
            'INSERT INTO Sekolah (kode_sekolah, nama_sekolah, jenis_sekolah) VALUES (?, ?, ?)',
            (request.form['kode_sekolah'], request.form['nama_sekolah'], request.form['jenis_sekolah'])
        )
        db.commit()
        flash('Data sekolah berhasil ditambahkan!', 'success')
        return redirect(url_for('input_sekolah'))
    return render_template('input_sekolah.html')
@app.route('/admin/input-pengajar', methods=['GET', 'POST'])
@role_required('admin')
def input_pengajar():
    if request.method == 'POST':
        db = get_db()
        kode_pengajar = request.form['kode_pengajar']
        nama_pengajar = request.form['nama_pengajar']
        program = request.form['program']
        username = kode_pengajar.lower().replace('-', '')
        password = generate_password_hash(username + '123')
        try:
            cursor = db.cursor()
            cursor.execute("INSERT INTO User (username, password, role) VALUES (?, ?, ?)",
                           (username, password, 'pengajar'))
            user_id = cursor.lastrowid
            cursor.execute("INSERT INTO Pengajar (kode_pengajar, nama_pengajar, program, user_id) VALUES (?, ?, ?, ?)",
                           (kode_pengajar, nama_pengajar, program, user_id))
            db.commit()
            flash(f"Pengajar '{nama_pengajar}' berhasil ditambahkan. Username: {username}", "success")
        except sqlite3.IntegrityError:
            db.rollback()
            flash(f"Error: Kode pengajar '{kode_pengajar}' atau username '{username}' sudah ada.", "error")
        return redirect(url_for('input_pengajar'))
    return render_template('input_pengajar.html')
@app.route('/admin/input-siswa', methods=['GET', 'POST'])
@role_required('admin')
def input_siswa():
    db = get_db()
    if request.method == 'POST':
        nama_siswa = request.form['nama_siswa']
        username = nama_siswa.lower().split()[0] + secrets.token_hex(2)
        password = generate_password_hash(username + '123')
        try:
            cursor = db.cursor()
            cursor.execute("INSERT INTO User (username, password, role) VALUES (?, ?, ?)",
                           (username, password, 'siswa'))
            user_id = cursor.lastrowid
            cursor.execute(
                'INSERT INTO Siswa (nama_siswa, kelas_tingkat, sekolah_id, program, user_id) VALUES (?, ?, ?, ?, ?)',
                (nama_siswa, request.form['kelas_tingkat'], request.form['sekolah_id'], request.form['program'], user_id)
            )
            db.commit()
            flash(f"Siswa '{nama_siswa}' berhasil ditambahkan. Username: {username}", "success")
        except sqlite3.Error as e:
            db.rollback()
            flash(f"Terjadi error: {e}", "error")
        return redirect(url_for('input_siswa'))
    sekolah_list = db.execute('SELECT id, kode_sekolah, nama_sekolah FROM Sekolah ORDER BY nama_sekolah').fetchall()
    return render_template('input_siswa.html', sekolah_list=sekolah_list)
@app.route('/admin/input-materi', methods=['GET', 'POST'])
@role_required('admin')
def input_materi():
    if request.method == 'POST':
        db = get_db()
        db.execute(
            'INSERT INTO Materi (program, pertemuan_ke, detail_materi) VALUES (?, ?, ?)',
            (request.form['program'], request.form['pertemuan_ke'], request.form['detail_materi'])
        )
        db.commit()
        flash('Materi baru berhasil ditambahkan!', 'success')
        return redirect(url_for('input_materi'))
    return render_template('input_materi.html')
@app.route('/admin/pengelompokan-kelas', methods=['GET', 'POST'])
@role_required('admin')
def pengelompokan_kelas():
    db = get_db()
    if request.method == 'POST':
        try:
            cursor = db.cursor()
            cursor.execute(
                'INSERT INTO Kelas (kode_kelas, nama_kelas, program_id, sekolah_id, pengajar_id, hari, waktu_mulai, waktu_akhir, tanggal_mulai) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (
                    request.form['kode_kelas'],
                    request.form['nama_kelas'],
                    request.form['program_id'],
                    request.form['sekolah_id'],
                    request.form['pengajar_id'],
                    request.form['hari'],
                    request.form['waktu_mulai'],
                    request.form['waktu_akhir'],
                    request.form['tanggal_mulai']
                )
            )
            kelas_id_baru = cursor.lastrowid
            siswa_ids = request.form.getlist('siswa_ids')
            if not siswa_ids:
                raise ValueError("Pilih minimal satu siswa.")
            for siswa_id in siswa_ids:
                db.execute('INSERT INTO KelasSiswa (kelas_id, siswa_id) VALUES (?, ?)', (kelas_id_baru, siswa_id))
            db.commit()
            flash(f"Kelas '{request.form['nama_kelas']}' berhasil dibuat dengan {len(siswa_ids)} siswa.", "success")
        except (sqlite3.IntegrityError, ValueError) as e:
            db.rollback()
            flash(f"Error: {e}", "error")
        return redirect(url_for('pengelompokan_kelas'))
    program_list = db.execute('SELECT id, nama_program FROM Program ORDER BY nama_program').fetchall()
    sekolah_list = db.execute('SELECT id, nama_sekolah FROM Sekolah ORDER BY nama_sekolah').fetchall()
    pengajar_list = db.execute('SELECT id, nama_pengajar FROM Pengajar ORDER BY nama_pengajar').fetchall()
    siswa_list = db.execute('SELECT id, nama_siswa FROM Siswa ORDER BY nama_siswa').fetchall()
    return render_template('pengelompokan_kelas.html', 
                           program_list=program_list,
                           sekolah_list=sekolah_list, 
                           pengajar_list=pengajar_list, 
                           siswa_list=siswa_list)
@app.route('/admin/upload/<tipe>', methods=['POST'])
@role_required('admin')
def upload_csv(tipe):
    """Fungsi untuk menangani upload dan proses data dari file CSV."""
    if 'csv_file' not in request.files:
        flash('Tidak ada file yang dipilih.', 'error')
        return redirect(request.referrer)
    file = request.files['csv_file']
    if file.filename == '':
        flash('Tidak ada file yang dipilih.', 'error')
        return redirect(request.referrer)
    if file and file.filename.endswith('.csv'):
        db = get_db()
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_reader = csv.reader(stream)
        header = next(csv_reader)
        success_count = 0
        fail_count = 0
        for row in csv_reader:
            try:
                if tipe == 'sekolah':
                    db.execute(
                        'INSERT INTO Sekolah (kode_sekolah, nama_sekolah, jenis_sekolah) VALUES (?, ?, ?)',
                        (row[0], row[1], row[2])
                    )
                elif tipe == 'pengajar':
                    kode_pengajar, nama_pengajar, program = row[0], row[1], row[2]
                    username = kode_pengajar.lower().replace('-', '')
                    password = generate_password_hash(username + '123')
                    cursor = db.cursor()
                    cursor.execute("INSERT INTO User (username, password, role) VALUES (?, ?, ?)",
                                   (username, password, 'pengajar'))
                    user_id = cursor.lastrowid
                    cursor.execute("INSERT INTO Pengajar (kode_pengajar, nama_pengajar, program, user_id) VALUES (?, ?, ?, ?)",
                                   (kode_pengajar, nama_pengajar, program, user_id))
                elif tipe == 'siswa':
                    nama_siswa, kelas_tingkat, kode_sekolah, program = row[0], row[1], row[2], row[3]
                    sekolah = db.execute('SELECT id FROM Sekolah WHERE kode_sekolah = ?', (kode_sekolah,)).fetchone()
                    if not sekolah:
                        fail_count += 1
                        continue
                    username = nama_siswa.lower().split()[0] + secrets.token_hex(2)
                    password = generate_password_hash(username + '123')
                    cursor = db.cursor()
                    cursor.execute("INSERT INTO User (username, password, role) VALUES (?, ?, ?)",
                                   (username, password, 'siswa'))
                    user_id = cursor.lastrowid
                    cursor.execute("INSERT INTO Siswa (nama_siswa, kelas_tingkat, sekolah_id, program, user_id) VALUES (?, ?, ?, ?, ?)",
                                   (nama_siswa, kelas_tingkat, sekolah['id'], program, user_id))
                elif tipe == 'materi':
                    db.execute(
                        'INSERT INTO Materi (program, pertemuan_ke, detail_materi) VALUES (?, ?, ?)',
                        (row[0], row[1], row[2])
                    )
                db.commit()
                success_count += 1
            except (sqlite3.IntegrityError, IndexError) as e:
                db.rollback()
                fail_count += 1
                print(f"Gagal memproses baris: {row}. Error: {e}")
        flash(f'Proses impor selesai. Berhasil: {success_count} baris, Gagal: {fail_count} baris.', 'success')
        return redirect(url_for('admin_manage_data', tipe=tipe))
    else:
        flash('Format file tidak valid. Harap upload file .csv', 'error')
        return redirect(request.referrer)
@app.route('/teacher/dashboard')
@role_required('pengajar')
def teacher_dashboard():
    db = get_db()
    teacher = db.execute('SELECT id FROM Pengajar WHERE user_id = ?', (session['user_id'],)).fetchone()
    if not teacher:
        flash('Profil pengajar tidak ditemukan', 'error')
        return redirect(url_for('logout'))
    classes = db.execute('''
        SELECT 
            k.id, 
            k.kode_kelas, 
            k.nama_kelas, 
            prg.nama_program,
            COUNT(ks.siswa_id) as jumlah_siswa
        FROM Kelas k
        LEFT JOIN Program prg ON k.program_id = prg.id
        LEFT JOIN KelasSiswa ks ON k.id = ks.kelas_id
        WHERE k.pengajar_id = ?
        GROUP BY k.id
        ORDER BY k.nama_kelas
    ''', (teacher['id'],)).fetchall()
    return render_template('teacher_dashboard.html', classes=classes)
@app.route('/teacher/pilih-kelas-absensi')
@role_required('pengajar')
def pilih_kelas_absensi():
    db = get_db()
    teacher = db.execute('SELECT id FROM Pengajar WHERE user_id = ?', (session['user_id'],)).fetchone()
    kelas_list = db.execute('''
        SELECT k.id, k.kode_kelas, k.nama_kelas, p.nama_pengajar 
        FROM Kelas k
        JOIN Pengajar p ON k.pengajar_id = p.id
        WHERE k.pengajar_id = ?
        ORDER BY k.nama_kelas
    ''', (teacher['id'],)).fetchall()
    return render_template('pilih_kelas_absensi.html', kelas_list=kelas_list)
@app.route('/teacher/absensi/<int:kelas_id>', methods=['GET', 'POST'])
@role_required('pengajar')
def absensi_kelas(kelas_id):
    db = get_db()
    kelas_info = db.execute('SELECT * FROM Kelas WHERE id = ?', (kelas_id,)).fetchone()
    if not kelas_info:
        flash('Kelas tidak ditemukan.', 'error')
        return redirect(url_for('teacher_dashboard'))
    try:
        jadwal_hari_str = kelas_info['hari']
        waktu_mulai_str = kelas_info['waktu_mulai']
        waktu_akhir_str = kelas_info['waktu_akhir']
        hari_map = {0: 'Senin', 1: 'Selasa', 2: 'Rabu', 3: 'Kamis', 4: 'Jumat', 5: 'Sabtu', 6: 'Minggu'}
        now = datetime.now()
        hari_sekarang_str = hari_map[now.weekday()]
        waktu_mulai = datetime.strptime(waktu_mulai_str, '%H:%M').time()
        waktu_akhir = datetime.strptime(waktu_akhir_str, '%H:%M').time()
        waktu_sekarang = now.time()
        if not (hari_sekarang_str == jadwal_hari_str and waktu_mulai <= waktu_sekarang <= waktu_akhir):
            flash(f"Akses absensi ditolak. Jadwal kelas ini adalah setiap {jadwal_hari_str}, dari pukul {waktu_mulai_str} hingga {waktu_akhir_str}.", 'error')
            return redirect(url_for('pilih_kelas_absensi'))
    except (ValueError, TypeError, KeyError):
        flash(f"Jadwal untuk kelas ini belum diatur dengan benar. Harap hubungi admin.", 'error')
        return redirect(url_for('pilih_kelas_absensi'))
    sesi_sebelumnya = db.execute('SELECT COUNT(id) FROM AbsensiSesi WHERE kelas_id = ?', (kelas_id,)).fetchone()[0]
    pertemuan_ke = sesi_sebelumnya + 1
    program_id = kelas_info['program_id']
    program_info = db.execute('SELECT nama_program FROM Program WHERE id = ?', (program_id,)).fetchone()
    nama_program = program_info['nama_program'] if program_info else ''
    materi_sesi_ini = db.execute('SELECT detail_materi FROM Materi WHERE program = ? AND pertemuan_ke = ?', (nama_program, pertemuan_ke)).fetchone()
    detail_materi = materi_sesi_ini['detail_materi'] if materi_sesi_ini else "Materi belum diinput untuk pertemuan ini."
    tanggal_hari_ini = datetime.now().strftime('%Y-%m-%d')
    if request.method == 'POST':
        selfie_data = request.form.get('selfie_data')
        if not selfie_data:
            flash('Foto selfie wajib diupload sebagai bukti kehadiran.', 'error')
            return redirect(url_for('absensi_kelas', kelas_id=kelas_id))
        pengajar_id = db.execute('SELECT id FROM Pengajar WHERE user_id = ?', (session['user_id'],)).fetchone()['id']
        materi_pembelajaran = request.form.get('materi_pembelajaran', detail_materi)
        tanggal = request.form.get('tanggal', tanggal_hari_ini)
        try:
            cursor = db.cursor()
            cursor.execute('INSERT INTO AbsensiSesi (kelas_id, tanggal, pengajar_id, foto_selfie, materi_pembelajaran) VALUES (?, ?, ?, ?, ?)', (kelas_id, tanggal, pengajar_id, selfie_data, materi_pembelajaran))
            sesi_id = cursor.lastrowid
            siswa_ids = request.form.getlist('siswa_id')
            for siswa_id in siswa_ids:
                jenis_sekolah = db.execute('SELECT sch.jenis_sekolah FROM Siswa s JOIN Sekolah sch ON s.sekolah_id = sch.id WHERE s.id = ?', (siswa_id,)).fetchone()['jenis_sekolah']
                prefix = "Alhamdulillah, " if jenis_sekolah == 'Muslim' else ""
                nilai_kehadiran = request.form.get(f'kehadiran_{siswa_id}')
                nilai_disiplin = request.form.get(f'kedisiplinan_{siswa_id}')
                nilai_kreatif = request.form.get(f'materi_kreativitas_{siswa_id}')
                nilai_kerjasama = request.form.get(f'kerjasama_{siswa_id}')
                desc_kehadiran = prefix + PENILAIAN_MAP['kehadiran'].get(nilai_kehadiran, '')
                desc_disiplin = prefix + PENILAIAN_MAP['kedisiplinan'].get(nilai_disiplin, '')
                desc_kreatif = prefix + PENILAIAN_MAP['materi_kreativitas'].get(nilai_kreatif, '')
                desc_kerjasama = prefix + PENILAIAN_MAP['kerjasama'].get(nilai_kerjasama, '')
                db.execute('INSERT INTO AbsensiSiswa (sesi_id, siswa_id, kehadiran_mutu, kehadiran, kedisiplinan_mutu, kedisiplinan, materi_kreativitas_mutu, materi_kreativitas, kerjasama_mutu, kerjasama) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (sesi_id, siswa_id, nilai_kehadiran, desc_kehadiran, nilai_disiplin, desc_disiplin, nilai_kreatif, desc_kreatif, nilai_kerjasama, desc_kerjasama))
            db.commit()
            flash('Data absensi dan penilaian berhasil disimpan!', 'success')
        except sqlite3.Error as e:
            db.rollback()
            flash(f'Terjadi error database: {e}', 'error')
        return redirect(url_for('pilih_kelas_absensi'))
    kelas_info_display = db.execute('SELECT k.*, p.nama_pengajar, prg.nama_program FROM Kelas k JOIN Pengajar p ON k.pengajar_id = p.id JOIN Program prg ON k.program_id = prg.id WHERE k.id = ?', (kelas_id,)).fetchone()
    siswa_di_kelas = db.execute('SELECT s.id, s.nama_siswa FROM Siswa s JOIN KelasSiswa ks ON s.id = ks.siswa_id WHERE ks.kelas_id = ? ORDER BY s.nama_siswa', (kelas_id,)).fetchall()
    return render_template('absensi_kelas.html', 
                           kelas_info=kelas_info_display,
                           siswa_di_kelas=siswa_di_kelas,
                           tanggal_hari_ini=tanggal_hari_ini,
                           pertemuan_ke=pertemuan_ke,
                           detail_materi=detail_materi)
@app.route('/teacher/rekap-pertemuan')
@role_required('pengajar')
def teacher_meeting_recap():
    db = get_db()
    teacher = db.execute('SELECT id, nama_pengajar FROM Pengajar WHERE user_id = ?', (session['user_id'],)).fetchone()
    meetings = db.execute('''
        SELECT 
            a.id as sesi_id, -- TAMBAHKAN BARIS INI
            a.tanggal, a.kelas_id, k.nama_kelas, k.kode_kelas,
            COALESCE(pengganti.nama_pengajar, asli.nama_pengajar) as nama_pengajar_sesi
        FROM AbsensiSesi a 
        JOIN Kelas k ON a.kelas_id = k.id
        JOIN Pengajar asli ON a.pengajar_id = asli.id
        LEFT JOIN Pengajar pengganti ON a.pengajar_pengganti_id = pengganti.id
        WHERE a.pengajar_id = ?
        GROUP BY a.tanggal, a.kelas_id
        ORDER BY a.tanggal DESC
    ''', (teacher['id'],)).fetchall()
    total_meetings = len(meetings)
    current_month_str = datetime.now().strftime('%Y-%m')
    current_month_meetings = sum(1 for m in meetings if m['tanggal'].startswith(current_month_str))
    monthly_summary = {}
    for meeting in meetings:
        month_key = meeting['tanggal'][:7]
        if month_key not in monthly_summary:
            monthly_summary[month_key] = 0
        monthly_summary[month_key] += 1
    return render_template('teacher_meeting_recap.html', 
                         teacher=teacher,
                         meetings=meetings, 
                         total_meetings=total_meetings,
                         current_month_meetings=current_month_meetings,
                         monthly_summary=monthly_summary)
@app.route('/api/sesi-foto/<int:sesi_id>')
@role_required('pengajar')
def get_sesi_foto(sesi_id):
    """API endpoint untuk mengambil data foto selfie berdasarkan ID sesi."""
    db = get_db()
    sesi = db.execute(
        'SELECT foto_selfie FROM AbsensiSesi WHERE id = ?', (sesi_id,)
    ).fetchone()
    if sesi and sesi['foto_selfie']:
        return jsonify({'foto_selfie': sesi['foto_selfie']})
    else:
        return jsonify({'error': 'Foto tidak ditemukan'}), 404
@app.route('/student/portfolio')
@role_required('siswa')
def student_portfolio():
    db = get_db()
    student = db.execute('SELECT * FROM Siswa WHERE user_id = ?', (session['user_id'],)).fetchone()
    if not student:
        flash('Profil siswa tidak ditemukan', 'error')
        return redirect(url_for('logout'))
    records = db.execute('''
        SELECT 
            asis.kehadiran_mutu, asis.kehadiran, 
            asis.kedisiplinan_mutu, asis.kedisiplinan, 
            asis.materi_kreativitas_mutu, asis.materi_kreativitas, 
            asis.kerjasama_mutu, asis.kerjasama,
            ases.tanggal, k.nama_kelas
        FROM AbsensiSiswa asis
        JOIN AbsensiSesi ases ON asis.sesi_id = ases.id
        JOIN Kelas k ON ases.kelas_id = k.id
        WHERE asis.siswa_id = ?
        ORDER BY ases.tanggal DESC
    ''', (student['id'],)).fetchall()
    monthly_records = {}
    for record in records:
        month_key = datetime.strptime(record['tanggal'], '%Y-%m-%d').strftime('%B %Y')
        if month_key not in monthly_records:
            monthly_records[month_key] = []
        monthly_records[month_key].append(record)
    return render_template('student_portfolio.html', 
                           monthly_records=monthly_records, 
                           student=student)
@app.route('/admin/jadwal-pengajar', methods=['GET', 'POST'])
@role_required('admin')
def admin_jadwal_pengajar():
    db = get_db()
    if request.method == 'POST':
        try:
            kelas_ids = request.form.getlist('kelas_id')
            for kelas_id in kelas_ids:
                hari = request.form.get(f'hari_{kelas_id}')
                waktu_mulai = request.form.get(f'waktu_mulai_{kelas_id}')
                waktu_akhir = request.form.get(f'waktu_akhir_{kelas_id}')
                tanggal_mulai = request.form.get(f'tanggal_mulai_{kelas_id}')
                db.execute(
                    'UPDATE Kelas SET hari = ?, waktu_mulai = ?, waktu_akhir = ?, tanggal_mulai = ? WHERE id = ?',
                    (hari, waktu_mulai, waktu_akhir, tanggal_mulai, kelas_id)
                )
            db.commit()
            flash('Jadwal berhasil diperbarui!', 'success')
        except sqlite3.Error as e:
            db.rollback()
            flash(f'Terjadi error saat memperbarui jadwal: {e}', 'error')
        pengajar_id = request.form.get('selected_pengajar_id')
        return redirect(url_for('admin_jadwal_pengajar', pengajar_id=pengajar_id))
    pengajar_list = db.execute('SELECT id, nama_pengajar FROM Pengajar ORDER BY nama_pengajar').fetchall()
    selected_pengajar_id = request.args.get('pengajar_id')
    kelas_list = None
    selected_pengajar = None
    if selected_pengajar_id:
        selected_pengajar = db.execute('SELECT * FROM Pengajar WHERE id = ?', (selected_pengajar_id,)).fetchone()
        kelas_list = db.execute(
            'SELECT id, nama_kelas, hari, waktu_mulai, waktu_akhir, tanggal_mulai FROM Kelas WHERE pengajar_id = ?', 
            (selected_pengajar_id,)
        ).fetchall()
    return render_template('admin_jadwal_pengajar.html', 
                           pengajar_list=pengajar_list,
                           kelas_list=kelas_list,
                           selected_pengajar=selected_pengajar)
@app.route('/print/portfolio/siswa/<int:siswa_id>')
@login_required 
def print_student_portfolio(siswa_id):
    db = get_db()
    student_info = db.execute('SELECT s.nama_siswa, k.nama_kelas, sch.jenis_sekolah FROM Siswa s LEFT JOIN KelasSiswa ks ON s.id = ks.siswa_id LEFT JOIN Kelas k ON ks.kelas_id = k.id LEFT JOIN Sekolah sch ON s.sekolah_id = sch.id WHERE s.id = ? LIMIT 1', (siswa_id,)).fetchone()
    if not student_info:
        flash('Data siswa tidak ditemukan', 'error')
        return redirect(request.referrer or url_for('admin_dashboard'))
    records_raw = db.execute('''
        SELECT 
            ases.tanggal, ases.materi_pembelajaran,
            asis.kehadiran_mutu, asis.kehadiran, 
            asis.kedisiplinan_mutu, asis.kedisiplinan, 
            asis.materi_kreativitas_mutu, asis.materi_kreativitas, 
            asis.kerjasama_mutu, asis.kerjasama
        FROM AbsensiSiswa asis
        JOIN AbsensiSesi ases ON asis.sesi_id = ases.id
        WHERE asis.siswa_id = ?
        ORDER BY ases.tanggal ASC
    ''', (siswa_id,)).fetchall()
    processed_records = []
    for row in records_raw:
        record = dict(row)
        record['tanggal_formatted'] = datetime.strptime(record['tanggal'], '%Y-%m-%d').strftime('%d/%m/%Y')
        processed_records.append(record)
    monthly_records = {}
    for record in processed_records:
        month_key = datetime.strptime(record['tanggal'], '%Y-%m-%d').strftime('%B %Y')
        if month_key not in monthly_records:
            monthly_records[month_key] = []
        monthly_records[month_key].append(record)
    return render_template('print_portfolio_siswa.html', 
                           student=student_info, 
                           monthly_records=monthly_records,
                           report_date=datetime.now().strftime('%d %B %Y'))
@app.route('/admin/kelola-sesi')
@role_required('admin')
def admin_kelola_sesi():
    db = get_db()
    classes = db.execute('''
        SELECT 
            k.id, k.nama_kelas, k.kode_kelas,
            p.nama_program,
            pg.nama_pengajar
        FROM Kelas k
        LEFT JOIN Program p ON k.program_id = p.id
        LEFT JOIN Pengajar pg ON k.pengajar_id = pg.id
        ORDER BY k.nama_kelas
    ''').fetchall()
    return render_template('admin_kelola_sesi.html', classes=classes)
@app.route('/admin/sesi-manual/<int:kelas_id>', methods=['GET', 'POST'])
@role_required('admin')
def admin_form_sesi_manual(kelas_id):
    db = get_db()
    kelas_info = db.execute('''
        SELECT k.id, k.nama_kelas, k.pengajar_id, pg.nama_pengajar 
        FROM Kelas k 
        JOIN Pengajar pg ON k.pengajar_id = pg.id 
        WHERE k.id = ?
    ''', (kelas_id,)).fetchone()
    if not kelas_info:
        flash('Kelas tidak ditemukan.', 'error')
        return redirect(url_for('admin_kelola_sesi'))
    if request.method == 'POST':
        tanggal = request.form['tanggal']
        pengajar_utama_id = kelas_info['pengajar_id']
        pengajar_pengganti_id = request.form.get('pengajar_pengganti_id')
        materi = request.form['materi_pembelajaran']
        if not pengajar_pengganti_id:
            pengajar_pengganti_id = None
        try:
            db.execute('''
                INSERT INTO AbsensiSesi (kelas_id, tanggal, pengajar_id, pengajar_pengganti_id, materi_pembelajaran, foto_selfie)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (kelas_id, tanggal, pengajar_utama_id, pengajar_pengganti_id, materi, 'MANUAL_ADMIN'))
            db.commit()
            flash('Sesi manual berhasil dibuat. Pengajar yang bersangkutan sekarang dapat mengisi penilaian.', 'success')
        except sqlite3.Error as e:
            db.rollback()
            flash(f'Gagal membuat sesi: {e}', 'error')
        return redirect(url_for('admin_kelola_sesi'))
    pengajar_list = db.execute('SELECT id, nama_pengajar FROM Pengajar ORDER BY nama_pengajar').fetchall()
    return render_template('admin_form_sesi_manual.html', 
                           kelas_info=kelas_info, 
                           pengajar_list=pengajar_list,
                           now=datetime.now())
@app.route('/admin/laporan/pengajar')
@role_required('admin')
def admin_teacher_meetings():
    db = get_db()
    teacher_stats = db.execute('''
        SELECT 
            p.id, p.nama_pengajar, u.username,
            COUNT(a.id) as total_pertemuan,
            SUM(CASE WHEN strftime('%Y-%m', a.tanggal) = strftime('%Y-%m', 'now') THEN 1 ELSE 0 END) as pertemuan_bulan_ini
        FROM Pengajar p
        LEFT JOIN User u ON p.user_id = u.id
        LEFT JOIN AbsensiSesi a ON p.id = a.pengajar_id OR p.id = a.pengajar_pengganti_id
        GROUP BY p.id
        ORDER BY p.nama_pengajar
    ''').fetchall()
    selected_teacher_id = request.args.get('teacher_id')
    teacher_meetings = None
    meetings_this_month = 0
    if selected_teacher_id:
        teacher_meetings = db.execute('''
            SELECT 
                a.id, a.tanggal, k.nama_kelas, k.kode_kelas,
                COALESCE(pengganti.nama_pengajar, asli.nama_pengajar) as nama_pengajar_sesi,
                prog.nama_program
            FROM AbsensiSesi a
            JOIN Kelas k ON a.kelas_id = k.id
            JOIN Program prog ON k.program_id = prog.id
            JOIN Pengajar asli ON a.pengajar_id = asli.id
            LEFT JOIN Pengajar pengganti ON a.pengajar_pengganti_id = pengganti.id
            WHERE asli.id = ? OR pengganti.id = ?
            ORDER BY a.tanggal DESC
        ''', (selected_teacher_id, selected_teacher_id)).fetchall()
        if teacher_meetings:
            meetings_this_month = sum(1 for m in teacher_meetings if m['tanggal'].startswith(datetime.now().strftime('%Y-%m')))
    return render_template('admin_teacher_meetings.html', 
                           teacher_stats=teacher_stats, 
                           teacher_meetings=teacher_meetings,
                           meetings_this_month=meetings_this_month,
                           selected_teacher=selected_teacher_id)
@app.route('/admin/laporan-gaji', methods=['GET'])
@role_required('admin')
def admin_laporan_gaji():
    db = get_db()
    selected_periode = request.args.get('periode', datetime.now().strftime('%Y-%m'))
    selected_program_id = request.args.get('program_id', 'all')
    periodes = [(datetime.now() - timedelta(days=30*i)).strftime('%Y-%m') for i in range(6)]
    programs = db.execute('SELECT * FROM Program').fetchall()
    query = '''
        SELECT p.id, p.nama_pengajar, COUNT(a.id) as jumlah
        FROM Pengajar p
        JOIN AbsensiSesi a ON (p.id = a.pengajar_id OR p.id = a.pengajar_pengganti_id)
        JOIN Kelas k ON a.kelas_id = k.id
        WHERE strftime('%Y-%m', a.tanggal) = ?
    '''
    params = [selected_periode]
    if selected_program_id != 'all':
        query += ' AND k.program_id = ?'
        params.append(selected_program_id)
    query += ' GROUP BY p.id ORDER BY p.nama_pengajar'
    teacher_reports = db.execute(query, params).fetchall()
    return render_template('admin_laporan_gaji.html',
                           reports=teacher_reports,
                           periodes=periodes,
                           programs=programs,
                           selected_periode=selected_periode,
                           selected_program_id=selected_program_id)
@app.route('/admin/slip-gaji/create', methods=['GET', 'POST'])
@role_required('admin')
def admin_create_slip_gaji():
    db = get_db()
    if request.method == 'POST':
        pengajar_id = request.form['pengajar_id']
        periode = request.form['periode']
        transport = request.form.get('transport_pengajaran', 0)
        marketing = request.form.get('tunjangan_marketing', 0)
        tugas_tambahan = request.form.get('tunjangan_tugas_tambahan', 0)
        lain_lain = request.form.get('tunjangan_lain_lain', 0)
        total = int(transport or 0) + int(marketing or 0) + int(tugas_tambahan or 0) + int(lain_lain or 0)
        try:
            cursor = db.cursor()
            existing_slip = cursor.execute('SELECT id FROM Gaji WHERE pengajar_id = ? AND periode = ?', (pengajar_id, periode)).fetchone()
            if existing_slip:
                cursor.execute('''
                    UPDATE Gaji SET transport_pengajaran = ?, tunjangan_marketing = ?, tunjangan_tugas_tambahan = ?, tunjangan_lain_lain = ?, total_gaji = ?, tanggal_dibuat = ?
                    WHERE id = ?
                ''', (transport, marketing, tugas_tambahan, lain_lain, total, datetime.now().strftime('%Y-%m-%d'), existing_slip['id']))
                gaji_id = existing_slip['id']
            else:
                cursor.execute('''
                    INSERT INTO Gaji (pengajar_id, periode, transport_pengajaran, tunjangan_marketing, tunjangan_tugas_tambahan, tunjangan_lain_lain, total_gaji, tanggal_dibuat)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (pengajar_id, periode, transport, marketing, tugas_tambahan, lain_lain, total, datetime.now().strftime('%Y-%m-%d')))
                gaji_id = cursor.lastrowid
            db.commit()
            return redirect(url_for('print_slip_gaji', gaji_id=gaji_id))
        except sqlite3.Error as e:
            db.rollback()
            flash(f'Gagal menyimpan slip gaji: {e}', 'error')
            return redirect(url_for('admin_laporan_gaji'))
    pengajar_id = request.args.get('pengajar_id')
    periode = request.args.get('periode')
    jumlah_sesi = request.args.get('jumlah', 0, type=int)
    tarif_per_sesi = 50000
    transport_value = jumlah_sesi * tarif_per_sesi
    pengajar = db.execute('SELECT * FROM Pengajar WHERE id = ?', (pengajar_id,)).fetchone()
    return render_template('admin_form_gaji.html',
                           pengajar=pengajar,
                           periode=periode,
                           transport_value=transport_value)
    pengajar_id = request.args.get('pengajar_id')
    periode = request.args.get('periode')
    jumlah_sesi = request.args.get('jumlah', 0, type=int)
    tarif_per_sesi = 50000
    transport_value = jumlah_sesi * tarif_per_sesi
    pengajar = db.execute('SELECT * FROM Pengajar WHERE id = ?', (pengajar_id,)).fetchone()
    return render_template('admin_form_gaji.html',
                           pengajar=pengajar,
                           periode=periode,
                           transport_value=transport_value)
@app.route('/print/slip-gaji/<int:gaji_id>')
@login_required
def print_slip_gaji(gaji_id):
    db = get_db()
    gaji_data = db.execute('''
        SELECT g.*, p.nama_pengajar
        FROM Gaji g
        JOIN Pengajar p ON g.pengajar_id = p.id
        WHERE g.id = ?
    ''', (gaji_id,)).fetchone()
    if not gaji_data:
        flash('Slip gaji tidak ditemukan', 'error')
        return redirect(url_for('admin_laporan_gaji'))
    return render_template('print_slip_gaji.html', slip=gaji_data)
def format_deskripsi(deskripsi, jenis_sekolah):
    """Filter untuk menghapus 'Alhamdulillah,' atau 'Alhamdulillah ' dari deskripsi jika sekolah non-muslim."""
    if not deskripsi:
        return ""
    if jenis_sekolah != 'Muslim':
        if deskripsi.lower().startswith('alhamdulillah,'):
            return deskripsi[len('alhamdulillah,'):].strip()
        if deskripsi.lower().startswith('alhamdulillah'):
            return deskripsi[len('alhamdulillah'):].strip()
    return deskripsi
def to_rupiah(value):
    """Format integer as Rupiah currency."""
    if value is None: return "Rp 0"
    return f"Rp {value:,}".replace(',', '.')
app.jinja_env.filters['to_rupiah'] = to_rupiah
app.jinja_env.filters['format_deskripsi'] = format_deskripsi
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
