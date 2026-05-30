import os
import shutil

from logging_setup import logger


class NotepadHistoryCleaner:

    def __init__(self):

        self.tabstate_path = os.path.join(

            os.environ.get("LOCALAPPDATA", ""),

            "Packages",
            "Microsoft.WindowsNotepad_8wekyb3d8bbwe",
            "LocalState",
            "TabState",
        )

    # =====================================================
    # CLEAR HISTORY
    # =====================================================
    def clear_history(self):

        logger.info("TabState削除開始: path=%s", self.tabstate_path)

        if not os.path.exists(self.tabstate_path):

            logger.warning("TabState不存在: path=%s", self.tabstate_path)
            return (
                False,
                "TabState フォルダが存在しません",
            )

        deleted_count = 0

        try:

            # -----------------------------------------
            # FILE COUNT
            # -----------------------------------------
            for _, _, files in os.walk(
                self.tabstate_path
            ):

                deleted_count += len(files)

            # -----------------------------------------
            # DELETE
            # -----------------------------------------
            shutil.rmtree(self.tabstate_path)

            logger.info("TabState削除成功: deleted=%s", deleted_count)

            return (
                True,
                f"{deleted_count} 件削除しました",
            )

        except Exception as e:

            logger.exception("TabState削除失敗")

            return (
                False,
                str(e),
            )