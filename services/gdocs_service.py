import os
import io
import re
import markdown
import base64
import urllib.request
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from google.auth.exceptions import RefreshError

SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive'
]

class GDocsService:
    def __init__(self):
        self.creds = None
        self._authenticate()

    def _authenticate(self):
        if os.path.exists('token.json'):
            self.creds = Credentials.from_authorized_user_file('token.json', SCOPES)
            
        if not self.creds or not self.creds.valid:
            refreshed = False
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                    refreshed = True
                except RefreshError:
                    if os.path.exists('token.json'):
                        os.remove('token.json')
                    self.creds = None

            if not refreshed or not self.creds:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                self.creds = flow.run_local_server(port=0)

            with open('token.json', 'w') as token:
                token.write(self.creds.to_json())

        self.drive_service = build('drive', 'v3', credentials=self.creds)
        self.docs_service = build('docs', 'v1', credentials=self.creds)

    @staticmethod
    def extract_file_id(url_or_id: str) -> str:
        url_or_id = url_or_id.strip()
        match = re.search(r'/d/([a-zA-Z0-9_-]+)', url_or_id)
        if match:
            return match.group(1)
        match_id = re.search(r'id=([a-zA-Z0-9_-]+)', url_or_id)
        if match_id:
            return match_id.group(1)
        return url_or_id

    def fetch_drive_file(self, url_or_id: str) -> dict:
        file_id = self.extract_file_id(url_or_id)
        meta = self.drive_service.files().get(fileId=file_id, fields='id, name, mimeType').execute()
        mime_type = meta.get('mimeType', '')
        file_name = meta.get('name', 'drive_file')
        file_buffer = io.BytesIO()

        if mime_type == 'application/vnd.google-apps.document':
            request = self.drive_service.files().export_media(fileId=file_id, mimeType='text/plain')
            downloader = MediaIoBaseDownload(file_buffer, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            return {"name": f"{file_name}.txt", "mime_type": "text/plain", "bytes": file_buffer.getvalue()}

        if mime_type == 'application/vnd.google-apps.presentation':
            request = self.drive_service.files().export_media(fileId=file_id, mimeType='application/pdf')
            downloader = MediaIoBaseDownload(file_buffer, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            return {"name": f"{file_name}.pdf", "mime_type": "application/pdf", "bytes": file_buffer.getvalue()}

        request = self.drive_service.files().get_media(fileId=file_id)
        downloader = MediaIoBaseDownload(file_buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

        return {"name": file_name, "mime_type": mime_type if mime_type else "application/octet-stream", "bytes": file_buffer.getvalue()}

    def _convert_mermaid_to_png_bytes(self, mermaid_code: str) -> bytes | None:
        """Convertit un code Mermaid en PNG via mermaid.ink pour l'insertion dans Google Docs."""
        try:
            import requests
            encoded = base64.urlsafe_b64encode(mermaid_code.encode("utf-8")).decode("ascii")
            res = requests.get(f"https://mermaid.ink/img/{encoded}?bgColor=FFFFFF", timeout=12)
            return res.content if res.status_code == 200 else None
        except Exception as e:
            print(f"[GDocsService] Erreur Mermaid PNG : {e}")
            return None

    def _upload_temp_image(self, png_bytes: bytes) -> tuple[str | None, str | None]:
        """Envoie l'image sur Google Drive en accès public temporaire pour l'injection Docs."""
        media = MediaIoBaseUpload(io.BytesIO(png_bytes), mimetype='image/png', resumable=False)
        meta = {'name': 'schema_temp.png'}
        file = self.drive_service.files().create(body=meta, media_body=media, fields='id, webContentLink').execute()
        file_id = file.get('id')

        # Donner l'accès lecture à l'API Docs
        self.drive_service.permissions().create(
            fileId=file_id,
            body={'type': 'anyone', 'role': 'reader'}
        ).execute()

        return file.get('webContentLink'), file_id

    def _cleanup_temp_files(self, file_ids: list[str]):
        """Supprime les fichiers temporaires créés, et purge les orphelins résiduels."""
        import time
        # Délai de sécurité pour laisser à Google Docs le temps de rapatrier l'image
        time.sleep(1.0)

        # 1. Suppression des fichiers de la génération en cours
        for f_id in file_ids:
            try:
                self.drive_service.files().delete(fileId=f_id).execute()
            except Exception as e:
                print(f"[GDocsService] Erreur lors de la suppression de {f_id} : {e}")

        # 2. Nettoyage des anciens fichiers orphelins restés sur le Drive
        try:
            query = "name = 'schema_temp.png' and trashed = false"
            results = self.drive_service.files().list(q=query, fields="files(id, name)").execute()
            orphans = results.get('files', [])
            for orphan in orphans:
                try:
                    self.drive_service.files().delete(fileId=orphan['id']).execute()
                    print(f"[GDocsService] Fichier orphelin purgé : {orphan['id']}")
                except Exception:
                    pass
        except Exception as e:
            print(f"[GDocsService] Erreur lors du balayage des orphelins : {e}")

    def create_adapted_doc(self, course_markdown: str, title: str = "Fiche de Révision 4ème", mermaid_code: str | None = None) -> str:
        processed_md = course_markdown
        temp_file_ids = []

        # Marqueur et pré-conversion pour la carte mentale
        mermaid_tag = "{{MERMAID_IMG}}"
        mermaid_png = None
        if mermaid_code and mermaid_code.strip():
            mermaid_png = self._convert_mermaid_to_png_bytes(mermaid_code)
            if mermaid_png:
                processed_md += f"\n\n## 🗺️ Carte Mentale Visuelle\n\n{mermaid_tag}\n\n"
            else:
                print("[GDocsService] Avertissement : Impossible de récupérer le PNG de la carte mentale Mermaid.")

        # Stylisation du texte rouge
        processed_md = re.sub(r':red\[(.*?)\]', r'<font color="#d90429"><b>\1</b></font>', processed_md)
        processed_md = re.sub(r'<span[^>]*style="[^"]*color:\s*#[a-fA-F0-9]+[^"]*"[^>]*>(.*?)</span\s*>', r'<font color="#d90429"><b>\1</b></font>', processed_md)
        processed_md = re.sub(r'`(<font color="#d90429"><b>.*?</b></font>)`', r'\1', processed_md)

        # 1. Extraction et remplacement des SVG par un marqueur unique
        svg_matches = list(re.finditer(r'<svg[\s\S]*?</svg>', processed_md, flags=re.IGNORECASE))
        placeholders = []

        for idx, match in enumerate(svg_matches):
            svg_code = match.group(0)
            tag = f"{{{{SCHEMA_IMG_{idx}}}}}"
            placeholders.append((tag, svg_code))
            processed_md = processed_md.replace(svg_code, f"\n\n{tag}\n\n", 1)

        # 2. Conversion Markdown -> HTML
        html_body = markdown.markdown(processed_md, extensions=['extra', 'nl2br'])
        full_html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; font-size: 11pt; line-height: 1.5; color: #111;">
{html_body}
</body>
</html>"""

        # 3. Création initiale du Google Doc depuis le HTML
        media = MediaIoBaseUpload(io.BytesIO(full_html.encode('utf-8')), mimetype='text/html', resumable=True)
        doc_file = self.drive_service.files().create(
            body={'name': title, 'mimeType': 'application/vnd.google-apps.document'},
            media_body=media,
            fields='id'
        ).execute()

        doc_id = doc_file.get('id')

        # 4 & 5. Insertion des images avec garantie de suppression via finally
        try:
            # Insertion carte mentale
            if mermaid_png:
                m_url, m_id = self._upload_temp_image(mermaid_png)
                if m_id:
                    temp_file_ids.append(m_id)
                if m_url:
                    self._replace_tag_with_image(doc_id, mermaid_tag, m_url, width_pt=500)
                else:
                    self._remove_tag(doc_id, mermaid_tag)

            # Insertion schémas SVG
            for tag, svg_code in placeholders:
                png_bytes = self._convert_svg_to_png_bytes(svg_code)
                if not png_bytes:
                    self._remove_tag(doc_id, tag)
                    continue

                img_url, img_id = self._upload_temp_image(png_bytes)
                if img_id:
                    temp_file_ids.append(img_id)
                if not img_url:
                    self._remove_tag(doc_id, tag)
                    continue

                self._replace_tag_with_image(doc_id, tag, img_url, width_pt=450)
        finally:
            # Exécuté systématiquement, même en cas de crash
            self._cleanup_temp_files(temp_file_ids)

        return f"https://docs.google.com/document/d/{doc_id}/edit"            

    def _convert_svg_to_png_bytes(self, svg_code: str) -> bytes | None:
        try:
            clean_svg = svg_code.strip()
            if 'xmlns=' not in clean_svg:
                clean_svg = re.sub(r'<svg\b', '<svg xmlns="http://www.w3.org/2000/svg"', clean_svg, count=1, flags=re.IGNORECASE)

            clean_svg = re.sub(r'&(?!(amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)', '&amp;', clean_svg)
            clean_svg = re.sub(r'<defs[\s\S]*?</defs>', '', clean_svg, flags=re.IGNORECASE)
            clean_svg = re.sub(r'<style[\s\S]*?</style>', '', clean_svg, flags=re.IGNORECASE)
            clean_svg = re.sub(r'marker-end="[^"]*"', '', clean_svg, flags=re.IGNORECASE)
            clean_svg = re.sub(r'<svg\b([^>]*?)\s+style="[^"]*"', r'<svg\1', clean_svg, flags=re.IGNORECASE)

            viewbox_match = re.search(r'viewBox="0\s+0\s+(\d+)\s+(\d+)"', clean_svg, flags=re.IGNORECASE)
            if viewbox_match and 'width=' not in clean_svg:
                w, h = viewbox_match.group(1), viewbox_match.group(2)
                clean_svg = re.sub(r'<svg\b', f'<svg width="{w}" height="{h}"', clean_svg, count=1, flags=re.IGNORECASE)

            try:
                import resvg_py
                return bytes(resvg_py.svg_to_bytes(clean_svg))
            except ImportError:
                svg_io = io.StringIO(clean_svg)
                drawing = svg2rlg(svg_io)
                if drawing:
                    png_io = io.BytesIO()
                    renderPM.drawToFile(drawing, png_io, fmt='PNG')
                    return png_io.getvalue()
            return None
        except Exception as e:
            print(f"[GDocsService] Erreur conversion SVG : {e}")
            return None

    def _convert_mermaid_to_png_bytes(self, mermaid_code: str) -> bytes | None:
        try:
            b64_bytes = base64.b64encode(mermaid_code.strip().encode('utf-8'))
            b64_str = b64_bytes.decode('ascii')
            url = f"https://mermaid.ink/img/{b64_str}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=12) as response:
                if response.status == 200:
                    return response.read()
            return None
        except Exception as e:
            print(f"[GDocsService] Erreur conversion Mermaid en PNG : {e}")
            return None

    def _replace_tag_with_image(self, doc_id: str, tag: str, img_url: str, width_pt: int = 450):
        doc_data = self.docs_service.documents().get(documentId=doc_id).execute()
        doc_content = doc_data.get('body', {}).get('content', [])
        insert_index = None

        for element in doc_content:
            if 'paragraph' in element:
                full_p_text = "".join(p.get('textRun', {}).get('content', '') for p in element['paragraph'].get('elements', []))
                if tag in full_p_text:
                    p_start = element.get('startIndex', 0)
                    offset = full_p_text.find(tag)
                    insert_index = p_start + offset
                    break

        if insert_index is not None:
            requests_payload = [
                {
                    'deleteContentRange': {
                        'range': {
                            'startIndex': insert_index,
                            'endIndex': insert_index + len(tag)
                        }
                    }
                },
                {
                    'insertInlineImage': {
                        'location': {'index': insert_index},
                        'uri': img_url,
                        'objectSize': {
                            'width': {'magnitude': width_pt, 'unit': 'PT'}
                        }
                    }
                }
            ]
            self.docs_service.documents().batchUpdate(documentId=doc_id, body={'requests': requests_payload}).execute()

    def _remove_tag(self, doc_id: str, tag: str):
        """Supprime proprement un marqueur texte résiduel dans le document si l'image n'a pas pu être générée."""
        try:
            doc_data = self.docs_service.documents().get(documentId=doc_id).execute()
            doc_content = doc_data.get('body', {}).get('content', [])
            for element in doc_content:
                if 'paragraph' in element:
                    full_p_text = "".join(p.get('textRun', {}).get('content', '') for p in element['paragraph'].get('elements', []))
                    if tag in full_p_text:
                        p_start = element.get('startIndex', 0)
                        offset = full_p_text.find(tag)
                        idx = p_start + offset
                        self.docs_service.documents().batchUpdate(
                            documentId=doc_id,
                            body={'requests': [{'deleteContentRange': {'range': {'startIndex': idx, 'endIndex': idx + len(tag)}}}]}
                        ).execute()
                        break
        except Exception as e:
            print(f"[GDocsService] Erreur suppression tag résiduel {tag} : {e}")