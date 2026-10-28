extends RefCounted
class_name AdventureLevelPaths

## 冒险模式 50 关配置文件的路径清单，由 tools/gen_adventure_levels.py 自动生成。
## 请勿手工修改本文件；调整关卡请改生成器的 LEVELS 数据表后重跑。
## 顺序即关卡顺序（1-1 到 5-10），选关界面按此顺序铺开并计算解锁进度。
const PATHS: Array[String] = [
	"res://resources/level_date_resource/mode_adventure_50/adv_1_01_front_day.tres",  # 1-1
	"res://resources/level_date_resource/mode_adventure_50/adv_1_02_front_day.tres",  # 1-2
	"res://resources/level_date_resource/mode_adventure_50/adv_1_03_front_day.tres",  # 1-3
	"res://resources/level_date_resource/mode_adventure_50/adv_1_04_front_day.tres",  # 1-4
	"res://resources/level_date_resource/mode_adventure_50/adv_1_05_front_day.tres",  # 1-5
	"res://resources/level_date_resource/mode_adventure_50/adv_1_06_front_day.tres",  # 1-6
	"res://resources/level_date_resource/mode_adventure_50/adv_1_07_front_day.tres",  # 1-7
	"res://resources/level_date_resource/mode_adventure_50/adv_1_08_front_day.tres",  # 1-8
	"res://resources/level_date_resource/mode_adventure_50/adv_1_09_front_day.tres",  # 1-9
	"res://resources/level_date_resource/mode_adventure_50/adv_1_10_front_day.tres",  # 1-10
	"res://resources/level_date_resource/mode_adventure_50/adv_2_01_front_night.tres",  # 2-1
	"res://resources/level_date_resource/mode_adventure_50/adv_2_02_front_night.tres",  # 2-2
	"res://resources/level_date_resource/mode_adventure_50/adv_2_03_front_night.tres",  # 2-3
	"res://resources/level_date_resource/mode_adventure_50/adv_2_04_front_night.tres",  # 2-4
	"res://resources/level_date_resource/mode_adventure_50/adv_2_05_front_night.tres",  # 2-5
	"res://resources/level_date_resource/mode_adventure_50/adv_2_06_front_night.tres",  # 2-6
	"res://resources/level_date_resource/mode_adventure_50/adv_2_07_front_night.tres",  # 2-7
	"res://resources/level_date_resource/mode_adventure_50/adv_2_08_front_night.tres",  # 2-8
	"res://resources/level_date_resource/mode_adventure_50/adv_2_09_front_night.tres",  # 2-9
	"res://resources/level_date_resource/mode_adventure_50/adv_2_10_front_night.tres",  # 2-10
	"res://resources/level_date_resource/mode_adventure_50/adv_3_01_back_pool.tres",  # 3-1
	"res://resources/level_date_resource/mode_adventure_50/adv_3_02_back_pool.tres",  # 3-2
	"res://resources/level_date_resource/mode_adventure_50/adv_3_03_back_pool.tres",  # 3-3
	"res://resources/level_date_resource/mode_adventure_50/adv_3_04_back_pool.tres",  # 3-4
	"res://resources/level_date_resource/mode_adventure_50/adv_3_05_back_pool.tres",  # 3-5
	"res://resources/level_date_resource/mode_adventure_50/adv_3_06_back_pool.tres",  # 3-6
	"res://resources/level_date_resource/mode_adventure_50/adv_3_07_back_pool.tres",  # 3-7
	"res://resources/level_date_resource/mode_adventure_50/adv_3_08_back_pool.tres",  # 3-8
	"res://resources/level_date_resource/mode_adventure_50/adv_3_09_back_pool.tres",  # 3-9
	"res://resources/level_date_resource/mode_adventure_50/adv_3_10_back_pool.tres",  # 3-10
	"res://resources/level_date_resource/mode_adventure_50/adv_4_01_back_fog.tres",  # 4-1
	"res://resources/level_date_resource/mode_adventure_50/adv_4_02_back_fog.tres",  # 4-2
	"res://resources/level_date_resource/mode_adventure_50/adv_4_03_back_fog.tres",  # 4-3
	"res://resources/level_date_resource/mode_adventure_50/adv_4_04_back_fog.tres",  # 4-4
	"res://resources/level_date_resource/mode_adventure_50/adv_4_05_back_fog.tres",  # 4-5
	"res://resources/level_date_resource/mode_adventure_50/adv_4_06_back_fog.tres",  # 4-6
	"res://resources/level_date_resource/mode_adventure_50/adv_4_07_back_fog.tres",  # 4-7
	"res://resources/level_date_resource/mode_adventure_50/adv_4_08_back_fog.tres",  # 4-8
	"res://resources/level_date_resource/mode_adventure_50/adv_4_09_back_fog.tres",  # 4-9
	"res://resources/level_date_resource/mode_adventure_50/adv_4_10_back_fog.tres",  # 4-10
	"res://resources/level_date_resource/mode_adventure_50/adv_5_01_roof_roof.tres",  # 5-1
	"res://resources/level_date_resource/mode_adventure_50/adv_5_02_roof_roof.tres",  # 5-2
	"res://resources/level_date_resource/mode_adventure_50/adv_5_03_roof_roof.tres",  # 5-3
	"res://resources/level_date_resource/mode_adventure_50/adv_5_04_roof_roof.tres",  # 5-4
	"res://resources/level_date_resource/mode_adventure_50/adv_5_05_roof_roof.tres",  # 5-5
	"res://resources/level_date_resource/mode_adventure_50/adv_5_06_roof_roof.tres",  # 5-6
	"res://resources/level_date_resource/mode_adventure_50/adv_5_07_roof_roof.tres",  # 5-7
	"res://resources/level_date_resource/mode_adventure_50/adv_5_08_roof_roof.tres",  # 5-8
	"res://resources/level_date_resource/mode_adventure_50/adv_5_09_roof_roof.tres",  # 5-9
	"res://resources/level_date_resource/mode_adventure_50/adv_5_10_roof_roofboss.tres",  # 5-10
]
