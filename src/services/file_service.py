from typing import Dict, List

from utils.logging import get_logger

logger = get_logger("services/file_service")

class FileService:
    @staticmethod
    def process_file(file_data: Dict) -> Dict:
        try:
            if file_data["type"] == "document":
                return {
                    "type": "document",
                    "file_id": file_data["file_id"]
                }
            elif file_data["type"] == "photo":
                return {
                    "type": "photo",
                    "file_id": file_data["file_id"]
                }
            elif file_data["type"] == "video":
                return {
                    "type": "video",
                    "file_id": file_data["file_id"]
                }
            elif file_data["type"] == "text":
                return {
                    "type": "text",
                    "content": file_data["content"]
                }
            else:
                raise ValueError(f"Unsupported file type: {file_data['type']}")
                
        except Exception as e:
            logger.exception(f"Error processing file: ")
            raise

    @staticmethod
    async def send_files_to_client(bot, client_id: int, files: List[Dict], 
                                 order_id: str, keyboard=None) -> None:
        try:
            first_message = True
            for file in files:
                caption = f"📥 Files for order #{order_id}" if first_message else None
                reply_markup = keyboard.as_markup() if first_message and keyboard else None
                
                if file["type"] == "document":
                    await bot.send_document(client_id, file["file_id"],
                                         caption=caption, reply_markup=reply_markup)
                elif file["type"] == "photo":
                    await bot.send_photo(client_id, file["file_id"],
                                      caption=caption, reply_markup=reply_markup)
                elif file["type"] == "video":
                    await bot.send_video(client_id, file["file_id"],
                                      caption=caption, reply_markup=reply_markup)
                elif file["type"] == "text":
                    text = f"💬 Message:\n{file['content']}\n\n"
                    if caption:
                        text += caption
                    await bot.send_message(client_id, text, reply_markup=reply_markup)
                    
                first_message = False
                
        except Exception as e:
            logger.exception(f"Error sending files to client: ")
            raise