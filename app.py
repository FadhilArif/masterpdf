import os
import io
import shutil
import zipfile
import tempfile
import subprocess
from pathlib import Path

import streamlit as st
from pypdf import PdfReader, PdfWriter


# ---------------- Helper ----------------

def tmpdir():
    return tempfile.mkdtemp(prefix="tk_")


def zip_folder(folder):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(Path(folder).rglob("*")):
            if p.is_file():
                z.write(p, p.relative_to(folder))
    buf.seek(0)
    return buf


def safe_name(name):
    clean = "".join(c if c.isalnum() or c in "._- " else "_" for c in name).strip()
    return clean or "file"


def save_upload(upload, folder):
    path = os.path.join(folder, safe_name(upload.name))
    with open(path, "wb") as f:
        f.write(upload.getbuffer())
    return path


def find_soffice():
    for name in ("soffice", "libreoffice"):
        p = shutil.which(name)
        if p:
            return p
    for p in (
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    ):
        if os.path.exists(p):
            return p
    return None


def parse_ranges(s, total):
    out = []
    for chunk in s.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            if "-" in chunk:
                a, b = chunk.split("-", 1)
                a, b = int(a), int(b)
                out.extend(range(a - 1, b))
            else:
                out.append(int(chunk) - 1)
        except ValueError:
            continue
    return [p for p in out if 0 <= p < total]


# ---------------- UI ----------------

st.set_page_config(page_title="Toolkit Pribadi", page_icon="🧰", layout="wide")

st.title("🧰 Toolkit Pribadi")
st.caption("Konversi dokumen, gambar, dan unduh media. 100% lokal, gratis, tanpa upload ke server.")

tabs = st.tabs([
    "📎 Gabung PDF",
    "✂️ Pisah PDF",
    "🖼️ Gambar → PDF",
    "📄 PDF → Gambar",
    "📝 Word → PDF",
    "📃 PDF → Word",
    "⬇️ Downloader",
])


# ---------------- 1. Gabung PDF ----------------
with tabs[0]:
    st.subheader("Gabung beberapa PDF jadi satu")
    files = st.file_uploader(
        "Pilih file PDF (urutan sesuai yang dipilih)",
        type="pdf", accept_multiple_files=True, key="merge",
    )
    if st.button("Gabung", key="merge_btn", type="primary"):
        if not files or len(files) < 2:
            st.warning("Pilih minimal 2 file PDF.")
        else:
            d = tmpdir()
            try:
                w = PdfWriter()
                for f in files:
                    path = save_upload(f, d)
                    for p in PdfReader(path).pages:
                        w.add_page(p)
                out = os.path.join(d, "gabungan.pdf")
                with open(out, "wb") as fp:
                    w.write(fp)
                st.success(f"Berhasil menggabung {len(files)} file.")
                st.download_button(
                    "⬇️ Unduh hasil", open(out, "rb"),
                    file_name="gabungan.pdf", mime="application/pdf",
                )
            except Exception as e:
                st.error(f"Gagal: {e}")


# ---------------- 2. Pisah PDF ----------------
with tabs[1]:
    st.subheader("Pisah / ekstrak halaman PDF")
    f = st.file_uploader("Pilih file PDF", type="pdf", key="split")
    mode = st.radio(
        "Mode",
        ["Pisah tiap halaman (ZIP)", "Ambil halaman tertentu"],
        horizontal=True,
    )
    rng = ""
    if mode == "Ambil halaman tertentu":
        rng = st.text_input("Halaman (contoh: 1-3,5,7-9)", value="1")

    if st.button("Proses", key="split_btn", type="primary"):
        if not f:
            st.warning("Pilih file PDF dulu.")
        else:
            d = tmpdir()
            try:
                path = save_upload(f, d)
                reader = PdfReader(path)
                total = len(reader.pages)

                if mode == "Pisah tiap halaman (ZIP)":
                    out_dir = os.path.join(d, "hasil")
                    os.makedirs(out_dir, exist_ok=True)
                    for i, page in enumerate(reader.pages):
                        w = PdfWriter()
                        w.add_page(page)
                        with open(os.path.join(out_dir, f"hal-{i+1:03d}.pdf"), "wb") as fp:
                            w.write(fp)
                    st.success(f"{total} halaman dipisah.")
                    st.download_button(
                        "⬇️ Unduh ZIP", zip_folder(out_dir),
                        file_name="hasil_split.zip", mime="application/zip",
                    )
                else:
                    pages = parse_ranges(rng, total)
                    if not pages:
                        st.warning("Tidak ada halaman valid.")
                    else:
                        w = PdfWriter()
                        for p in pages:
                            w.add_page(reader.pages[p])
                        out = os.path.join(d, "extract.pdf")
                        with open(out, "wb") as fp:
                            w.write(fp)
                        st.success(f"Diambil {len(pages)} halaman.")
                        st.download_button(
                            "⬇️ Unduh PDF", open(out, "rb"),
                            file_name="extract.pdf", mime="application/pdf",
                        )
            except Exception as e:
                st.error(f"Gagal: {e}")


# ---------------- 3. Gambar → PDF ----------------
with tabs[2]:
    st.subheader("Ubah gambar jadi PDF")
    imgs = st.file_uploader(
        "Pilih gambar (urutan sesuai yang dipilih)",
        type=["png", "jpg", "jpeg", "webp", "bmp", "tiff"],
        accept_multiple_files=True, key="img2pdf",
    )
    if st.button("Buat PDF", key="img2pdf_btn", type="primary"):
        if not imgs:
            st.warning("Pilih minimal 1 gambar.")
        else:
            d = tmpdir()
            try:
                import img2pdf
                paths = [save_upload(i, d) for i in imgs]
                out = os.path.join(d, "gambar.pdf")
                with open(out, "wb") as fp:
                    fp.write(img2pdf.convert(paths))
                st.success(f"{len(paths)} gambar digabung jadi PDF.")
                st.download_button(
                    "⬇️ Unduh PDF", open(out, "rb"),
                    file_name="gambar.pdf", mime="application/pdf",
                )
            except Exception as e:
                st.error(f"Gagal: {e}")


# ---------------- 4. PDF → Gambar ----------------
with tabs[3]:
    st.subheader("Ubah PDF jadi gambar")
    f = st.file_uploader("Pilih file PDF", type="pdf", key="pdf2img")
    c1, c2 = st.columns(2)
    dpi = c1.slider("Kualitas (DPI)", 72, 400, 150, 10)
    fmt = c2.selectbox("Format", ["PNG", "JPG"])

    if st.button("Konversi", key="pdf2img_btn", type="primary"):
        if not f:
            st.warning("Pilih file PDF dulu.")
        else:
            d = tmpdir()
            try:
                import fitz
                from PIL import Image

                path = save_upload(f, d)
                out_dir = os.path.join(d, "hasil")
                os.makedirs(out_dir, exist_ok=True)

                doc = fitz.open(path)
                for i, page in enumerate(doc):
                    pix = page.get_pixmap(dpi=dpi)
                    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                    ext = "png" if fmt == "PNG" else "jpg"
                    img.save(os.path.join(out_dir, f"hal-{i+1:03d}.{ext}"))

                st.success(f"{len(doc)} halaman dikonversi.")
                st.download_button(
                    "⬇️ Unduh ZIP", zip_folder(out_dir),
                    file_name="pdf_gambar.zip", mime="application/zip",
                )
            except Exception as e:
                st.error(f"Gagal: {e}")


# ---------------- 5. Word → PDF ----------------
with tabs[4]:
    st.subheader("Ubah Word jadi PDF")
    f = st.file_uploader(
        "Pilih file Word", type=["docx", "doc", "odt", "rtf"], key="w2p"
    )
    if st.button("Konversi", key="w2p_btn", type="primary"):
        if not f:
            st.warning("Pilih file Word dulu.")
        else:
            soffice = find_soffice()
            if not soffice:
                st.error(
                    "LibreOffice tidak ditemukan. Install LibreOffice dulu, "
                    "lalu pastikan perintah `soffice` bisa dijalankan dari terminal."
                )
            else:
                d = tmpdir()
                try:
                    path = save_upload(f, d)
                    out_dir = os.path.join(d, "out")
                    os.makedirs(out_dir, exist_ok=True)
                    subprocess.run(
                        [soffice, "--headless", "--convert-to", "pdf",
                         "--outdir", out_dir, path],
                        check=True, timeout=180,
                    )
                    pdfs = list(Path(out_dir).glob("*.pdf"))
                    if not pdfs:
                        st.error("Konversi gagal, tidak ada PDF yang dihasilkan.")
                    else:
                        st.success("Berhasil dikonversi.")
                        st.download_button(
                            "⬇️ Unduh PDF", open(pdfs[0], "rb"),
                            file_name=pdfs[0].name, mime="application/pdf",
                        )
                except Exception as e:
                    st.error(f"Gagal: {e}")


# ---------------- 6. PDF → Word ----------------
with tabs[5]:
    st.subheader("Ubah PDF jadi Word (.docx)")
    st.caption("Layout kompleks atau PDF hasil scan mungkin tidak sempurna.")
    f = st.file_uploader("Pilih file PDF", type="pdf", key="p2w")
    if st.button("Konversi", key="p2w_btn", type="primary"):
        if not f:
            st.warning("Pilih file PDF dulu.")
        else:
            d = tmpdir()
            try:
                from pdf2docx import Converter

                path = save_upload(f, d)
                out = os.path.join(d, "hasil.docx")
                with st.spinner("Memproses... (bisa lama untuk PDF besar)"):
                    cv = Converter(path)
                    cv.convert(out)
                    cv.close()

                st.success("Berhasil dikonversi.")
                st.download_button(
                    "⬇️ Unduh DOCX", open(out, "rb"),
                    file_name="hasil.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            except Exception as e:
                st.error(f"Gagal: {e}")


# ---------------- 7. Downloader ----------------
with tabs[6]:
    st.subheader("Unduh video / gambar (TikTok, Instagram, dll.)")
    st.caption(
        "Hanya untuk konten publik dan penggunaan pribadi. "
        "Patuhi hak cipta dan ToS platform."
    )
    urls = st.text_area(
        "Tempel URL (satu per baris)",
        height=140,
        placeholder="https://www.tiktok.com/@user/video/...\nhttps://www.instagram.com/reel/...",
    )

    if st.button("Unduh", key="dl_btn", type="primary"):
        list_url = [u.strip() for u in urls.splitlines() if u.strip()]
        if not list_url:
            st.warning("Masukkan minimal 1 URL.")
        else:
            import yt_dlp

            d = tmpdir()
            out_dir = os.path.join(d, "unduhan")
            os.makedirs(out_dir, exist_ok=True)

            opts = {
                "outtmpl": os.path.join(out_dir, "%(title).120s.%(ext)s"),
                "format": "bestvideo*+bestaudio/best",
                "merge_output_format": "mp4",
                "noplaylist": True,
                "quiet": True,
                "no_warnings": True,
                "ignoreerrors": True,
            }

            ok, fail = 0, 0
            with st.spinner("Mengunduh..."):
                with yt_dlp.YoutubeDL(opts) as ydl:
                    for u in list_url:
                        try:
                            ydl.download([u])
                            ok += 1
                        except Exception:
                            fail += 1

            files = [p for p in Path(out_dir).rglob("*") if p.is_file()]
            if files:
                msg = f"Selesai. {len(files)} file berhasil diunduh."
                if fail:
                    msg += f" {fail} URL gagal."
                st.success(msg)
                st.download_button(
                    "⬇️ Unduh ZIP", zip_folder(out_dir),
                    file_name="unduhan.zip", mime="application/zip",
                )
                with st.expander("Lihat daftar file"):
                    for p in files:
                        st.write(f"- {p.name}")
            else:
                st.error("Tidak ada file yang berhasil diunduh. Cek URL atau coba lagi nanti.")


st.divider()
st.caption("Semua proses berjalan lokal di komputer kamu. File sementara disimpan di folder temp sistem.")
