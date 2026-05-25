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
            
            count += 1
            
        return count
    
    def execute(self, key, overwrite_callback=None):

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

        os.makedirs(
            into_folder,
            exist_ok=True,
        )

        moved_count = 0
        skip_count = 0

        # =================================================
        # FILE LOOP
        # =================================================
        for name in os.listdir(out_folder):

            # ---------------------------------------------
            # IGNORE
            # ---------------------------------------------
            if name in ignore_list:

                continue

            src_path = os.path.join(
                out_folder,
                name,
            )

            dst_path = os.path.join(
                into_folder,
                name,
            )

            try:

                # =========================================
                # SAME NAME CHECK
                # =========================================
                if os.path.exists(dst_path):

                    overwrite = False

                    if overwrite_callback:

                        overwrite = overwrite_callback(
                            name,
                            src_path,
                            dst_path,
                        )

                    # NO
                    if not overwrite:

                        skip_count += 1
                        continue

                    # YES
                    if os.path.isfile(dst_path):

                        os.remove(dst_path)

                    elif os.path.isdir(dst_path):

                        shutil.rmtree(dst_path)

                # =========================================
                # MOVE
                # =========================================
                shutil.move(
                    src_path,
                    dst_path,
                )

                moved_count += 1

            except Exception as e:

                return (
                    False,
                    f"移動失敗 : {name}\n{str(e)}"
                )

        msg = (
            f"{moved_count} 件移動しました"
        )

        if skip_count > 0:

            msg += (
                f"\n{skip_count} 件スキップ"
            )

        return True, msg