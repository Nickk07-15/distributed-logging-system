import logging
import os
import shutil
import csv

import base64
import glob
import subprocess
from pyunpack import Archive, PatoolError

import exceptions.custom_exceptions as ce
from utils.helpers import timeit


logger = logging.getLogger(__name__)


class FileUtil:
    """
    Utility class for file operations
    """
    @staticmethod
    def decode_image_str(image_str: str, output_file: str) -> None:
        """
        Decode the image string and save it to a file

        Args:
            image_str (str): Image string
            output_file (str): Output file path

        Returns (None):

        """
        with open(output_file, mode="wb") as image_write_file:
            image_write_file.write((base64.b64decode(image_str)))

    @staticmethod
    def delete_object(path: str) -> None:
        """
        Deletes a file or directory

        Args:
            path (str): Path to the file or directory to be deleted

        Returns (None):

        Raises:
            FileNotFoundError: If the file or directory does not exist
            PermissionError: If the file or directory cannot be deleted
            ce.FilePathDeleteException: If there is an error deleting the file or directory
        """

        try:
            logger.info(f"Deleting {path}")

            if os.path.isfile(path) or os.path.islink(path):
                os.unlink(path)

            if os.path.isdir(path):
                shutil.rmtree(path)

        except FileNotFoundError as file_not_found_error:
            logger.error(f"File not found: {file_not_found_error}")
            logger.exception(f"File not found: {file_not_found_error}")
            raise FileNotFoundError(f"File not found: {file_not_found_error}")

        except PermissionError as permission_error:
            logger.error(f"Permission error: {permission_error}")
            logger.exception(f"Permission error: {permission_error}")
            raise PermissionError(f"Permission error: {permission_error}")

        except Exception as exception:
            logger.error(f"Error deleting file: {exception}")
            logger.exception(f"Error deleting file: {exception}")
            raise ce.FilePathDeleteException(f"Error deleting file: {exception}")

    @staticmethod
    def get_file_extension(file_path: str) -> str:
        """
        Get the file extension e.g. `.zip`, `.csv`, `.txt`, etc.

        Args:
            file_path (str): Path to the file

        Returns (str): Extension type of the file

        Raises:
            ValueError: If the file path is None or invalid

        """

        if file_path is None:
            raise ValueError("File path cannot be None")

        parameters = file_path.split(".")
        if len(parameters) == 0:
            raise ValueError("Invalid file path")

        extension = parameters[-1]
        return extension

    @staticmethod
    @timeit
    def unzip_file(zip_file_path: str, unzip_location: str, file_type: str = "*") -> list[str]:
        """
        Check the file_type of the provided file\n
        * If the file_type is a zip file, unzip the file with `unzip` library\n
        * If the file_type is 7z, then use `py7z` library to unzip the file\n

        Args:
            zip_file_path (str): Path to the zip file
            unzip_location (str): Directory to extract the zip file
            file_type (str): Type of the file to be unzipped, default is *

        Returns (list[str]):
            List of unzipped files

        Raises:
            ce.BadZipFileException: If there is an error unzipping the file
            Exception: If there is an error unzipping the file
        """

        try:
            logger.info(f"Unzipping file {zip_file_path} to {unzip_location}")
            extension = FileUtil.get_file_extension(zip_file_path)

            match extension:
                case "zip":
                    Archive(zip_file_path).extractall(unzip_location)

                case "7z":
                    unzip_command = f"7z x -aoa {zip_file_path} -o{unzip_location}"
                    return_value = subprocess.call(unzip_command, shell=True)
                    if return_value != 0:
                        logger.warning(f"Command {unzip_command} ran with error code {return_value}")
                        raise ce.BadZipFileException("Error unzipping file, could not extract")

            unzipped_file_list = glob.glob(f"{unzip_location}/*.{file_type}")
            if len(unzipped_file_list) == 0:
                # In case the zip file has been extracted, and no files are found,
                # the case should be stored in missed files
                logger.warning("No files found within the zip")
                raise ce.BadZipFileException("No files found within the zip")

            return unzipped_file_list

        except (PatoolError, ce.BadZipFileException) as zip_error:
            logger.warning(f"Error unzipping file: {zip_error}")
            raise ce.BadZipFileException(f"Error unzipping file: {zip_error}")

        except Exception as error:
            raise

    @staticmethod
    def delete_all_file_types(file_location: str, file_type: str) -> None:
        """
        Removes all the files from a directory based on the type of file

        Args:
            file_location (str): Directory path
            file_type (str): Type of file

        Returns (None):

        """
        file_type = f"*.{file_type}"
        file_list = glob.glob(os.path.join(file_location, file_type))

        for file in file_list:
            FileUtil.delete_object(file)

    @staticmethod
    def rename_file(file_path: str, new_file_name: str) -> str:
        """
        Renames a file, given the path and the new name

        Args:
            file_path (str): Path to the file
            new_file_name (str): New name of the file

        Returns (str):
            New file path

        """
        file_directory = os.path.dirname(file_path)
        new_file_path = os.path.join(file_directory, new_file_name)
        logger.debug(f"Renaming file {file_path} to {new_file_path}")
        os.rename(file_path, new_file_path)
        return new_file_path

    @staticmethod
    def write_csv(file_path: str, data: list[dict[str, any]]) -> None:
        """
        Write data to a CSV file

        Args:
            file_path (str): Path to the file
            data (list[dict[str, any]]): Data to be written to the file

        Returns (None):

        """
        with open(file_path, mode='w') as write_csv_file:
            writer = csv.DictWriter(write_csv_file, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
