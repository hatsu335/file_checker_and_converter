import os
import shutil


class MoveFileManager:

    def __init__(self, config):

        self.config = config

    # =====================================================
    # EXECUTE
    # =====================================================
    def count_target_files(self, key):
        
        move_config = self.config.get(key)
        
        if not move_config:
            return 0
        
        out_folder = move_config.get(
            "out_of_folder"
        )
        
        ignore_list = move_config.get(
            "ignore",
            [],
        )
        
        if not os.path.exists(out_folder):
            return 0
        
        count = 0
        
        for name in os.listdir(out_folder):
            
            src_path = os.path.join(
                out_folder,
                name,
            )
            
            # IGNORE
            if name in ignore_list:
                continue
            
            # IGNORE FOLDER (フォルダを移動しない設定)
            # if os.path.isdir(src_path):
            #     continue
            
            count += 1
            
        return count

    # =====================================================
    # EXECUTE
    # =====================================================
    def execute(self, key):

        move_config = self.config.get(key)

        if not move_config:

            return False, "設定が存在しません"

        out_folder = move_config.get(
            "out_of_folder"
        )

        into_folder = move_config.get(
            "into_folder"
        )

        ignore_list = move_config.get(
            "ignore",
            [],
        )

        if not os.path.exists(out_folder):

            return False, "移動元フォルダが存在しません"

        os.makedirs(into_folder, exist_ok=True)

        moved_count = 0

        # =================================================
        # FILE LOOP
        # =================================================
        for name in os.listdir(out_folder):

            src_path = os.path.join(
                out_folder,
                name,
            )

            # ---------------------------------------------
            # IGNORE
            # ---------------------------------------------
            if name in ignore_list:

                continue

            # ---------------------------------------------
            # FOLDER IGNORE
            # ---------------------------------------------
            # if os.path.isdir(src_path):

            #     continue

            dst_path = os.path.join(
                into_folder,
                name,
            )

            try:

                shutil.move(
                    src_path,
                    dst_path,
                )

                moved_count += 1

            except Exception as e:

                return (
                    False,
                    f"移動失敗 : {name} / {str(e)}"
                )

        return (
            True,
            f"{moved_count} 件移動しました"
        )