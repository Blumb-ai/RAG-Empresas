def execute_drive_script_folders():
    import io
    import re
    from googleapiclient.http import MediaIoBaseDownload
    from googleapiclient.errors import HttpError
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from dotenv import load_dotenv
    import os
    import json
    import logging


    def sanitize_filename(filename):
        # Elimina caracteres no válidos del nombre del archivo
        safe_filename = re.sub(r'[^a-zA-Z0-9_\-. ]', '', filename)
        # Trunca el archivo si es demasiado largo
        return safe_filename[:255]

    # Función para buscar archivos de forma recursiva en carpetas de Drive
    def search_and_download_files(service, folder_id, parent_path="./documentos"):
        # Lista todos los archivos en la carpeta actual
        logging.info("Iniciando descarga de archivos...")
        query = f"'{folder_id}' in parents"
        response = service.files().list(q=query, fields="files(id, name, mimeType, webViewLink)").execute()
        files = response.get('files', [])

        for file in files:
            # Sanitizar el nombre del archivo y construir el camino completo
            safe_file_name = sanitize_filename(file['name'])
            file_path = os.path.join(parent_path, safe_file_name)
            logging.info(f"Descargando archivo: {file_path}")
            if file['mimeType'] == 'application/vnd.google-apps.folder':  # Es una carpeta
                # Si no existe el directorio, créalo
                if not os.path.exists(file_path):
                    os.makedirs(file_path, exist_ok=True)
                search_and_download_files(service, file['id'], file_path)  # Búsqueda recursiva en la subcarpeta
            else:
                # Determinar el tipo de archivo y preparar el request de descarga
                if file['mimeType'] == 'application/vnd.google-apps.document':
                    request = service.files().export_media(fileId=file['id'], mimeType='application/pdf')
                    file_extension = '.pdf'  # Guardar como PDF
                elif file['mimeType'] == 'application/vnd.google-apps.spreadsheet':
                    request = service.files().export_media(fileId=file['id'], mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    file_extension = '.xlsx'  # Guardar como Excel
                elif file['mimeType'] == 'application/vnd.google-apps.presentation':
                    request = service.files().export_media(fileId=file['id'], mimeType='application/vnd.openxmlformats-officedocument.presentationml.presentation')
                    file_extension = '.pptx'  # Guardar como PowerPoint
                else:
                    # Para otros tipos de archivos, usa el método get_media
                    request = service.files().get_media(fileId=file['id'])
                    file_extension = ''  # Podrías querer determinar esto basado en el mimeType para mantener la extensión original

                file_path += file_extension
                os.makedirs(os.path.dirname(file_path), exist_ok=True)

                # Intenta descargar el archivo, maneja el error si el archivo es demasiado grande
                try:
                    fh = io.BytesIO()
                    downloader = MediaIoBaseDownload(fh, request)
                    done = False
                    while not done:
                        status, done = downloader.next_chunk()
                        print(f"Download {int(status.progress() * 100)}% of {file_path}")

                    # Guardar el archivo en la estructura de carpetas
                    with open(file_path, 'wb') as f:
                        f.write(fh.getvalue())
                        print(f"Archivo '{file_path}' descargado.")
                except HttpError as error:
                    logging.error(f"Error al descargar el archivo '{file_path}': {str(error)}")
                    if error.resp.status == 403 and 'exportSizeLimitExceeded' in str(error):
                        print(f"No se puede exportar el archivo '{file_path}' debido a que excede el límite de tamaño.")
                    else:
                        print(f"Error al descargar el archivo '{file_path}': {str(error)}")

                # Añade la URL del documento a source_documents independientemente de si se descargó o no
                source_documents[file_path] = file.get('webViewLink', 'URL no disponible')
            logging.info(f"Archivo '{file_path}' descargado.")

        logging.info("Descarga de archivos finalizada.")

    load_dotenv()  # Carga las variables de entorno del archivo .env

    #SCOPES = [os.getenv('SCOPES')]
    SCOPES = ['https://www.googleapis.com/auth/drive']
    #SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE')
    SERVICE_ACCOUNT_FILE = 'credentials/'
    

    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)

    service = build('drive', 'v3', credentials=credentials)

    # Carpeta raíz de Drive desde donde se inicia la búsqueda
    folder_id = os.getenv('FOLDER_DRIVE_ID')  # Carpeta de drive
    source_documents = {}

    search_and_download_files(service, folder_id)  # Comienza la búsqueda y descarga recursiva

    # Guarda los enlaces de los documentos en un archivo JSON
    with open('./documentos/source_documents.json', 'w') as fp:
        json.dump(source_documents, fp)

    print("Source documents guardados.")
    return source_documents
