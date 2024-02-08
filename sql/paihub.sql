SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for auto_review_rules
-- ----------------------------
DROP TABLE IF EXISTS `auto_review_rules`;
CREATE TABLE `auto_review_rules`  (
  `id` int NOT NULL COMMENT '自动审核表 主键',
  `work_id` int NULL DEFAULT NULL COMMENT '对那个作品类型进行匹配',
  `name` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL COMMENT '自动审核名称',
  `description` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL COMMENT '自动审核描述',
  `action` tinyint NULL DEFAULT NULL COMMENT '规则匹配时的操作 0拒绝 1通过',
  `status` tinyint NULL DEFAULT NULL COMMENT '规则是否启用',
  `rules` text CHARACTER SET utf8 COLLATE utf8_general_ci NULL COMMENT '包含多个正则表达式或规则的JSON结构',
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8 COLLATE = utf8_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for pixiv
-- ----------------------------
DROP TABLE IF EXISTS `pixiv`;
CREATE TABLE `pixiv`  (
  `id` bigint UNSIGNED NOT NULL,
  `title` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT 'Pixiv artwork title',
  `tags` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL COMMENT 'Pixiv artwork tags',
  `view_count` bigint UNSIGNED NULL DEFAULT NULL COMMENT 'Pixiv artwork views',
  `like_count` bigint UNSIGNED NULL DEFAULT NULL COMMENT 'Pixiv artwork likes',
  `love_count` bigint UNSIGNED NULL DEFAULT NULL COMMENT 'Pixiv artwork loves',
  `author_id` bigint UNSIGNED NULL DEFAULT NULL COMMENT 'Pixiv artwork author id',
  `create_time` datetime NULL DEFAULT NULL,
  `update_time` datetime NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `id`(`id` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8 COLLATE = utf8_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for push
-- ----------------------------
DROP TABLE IF EXISTS `push`;
CREATE TABLE `push`  (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '唯一ID',
  `review_id` bigint NULL DEFAULT NULL COMMENT '关联review表',
  `channel_id` bigint NULL DEFAULT NULL COMMENT '推送到的频道ID',
  `message_id` bigint NULL DEFAULT NULL,
  `status` tinyint NULL DEFAULT NULL COMMENT '推送状态（例如：“已推送”，“失败”等）',
  `ext` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL COMMENT '扩展字段',
  `create_by` int NOT NULL,
  `create_time` datetime NULL DEFAULT NULL,
  `update_by` int NULL DEFAULT NULL,
  `update_time` datetime NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `review_id`(`review_id` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8 COLLATE = utf8_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for review
-- ----------------------------
DROP TABLE IF EXISTS `review`;
CREATE TABLE `review`  (
  `id` bigint UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '审核ID',
  `work_id` bigint NOT NULL COMMENT '作品类型',
  `site_key` varchar(16) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL COMMENT '网站KeyName',
  `artwork_id` bigint NOT NULL COMMENT '数据库中的作品ID',
  `author_id` bigint NULL DEFAULT NULL,
  `status` enum('WAIT','REJECT','PASS','ERROR','MOVE','NOT_FOUND') CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL COMMENT '审核状态 如拒绝或者通过',
  `auto` tinyint NULL DEFAULT NULL COMMENT '是否为自动审核',
  `ext` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL COMMENT '自定义信息 JSON格式',
  `create_by` int NULL DEFAULT NULL,
  `create_time` datetime NULL DEFAULT NULL,
  `update_by` int NULL DEFAULT NULL,
  `update_time` datetime NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8 COLLATE = utf8_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for review_black_author
-- ----------------------------
DROP TABLE IF EXISTS `review_black_author`;
CREATE TABLE `review_black_author`  (
  `id` int NOT NULL,
  `site_key` varchar(16) CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL,
  `author_id` int NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8 COLLATE = utf8_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for review_white_author
-- ----------------------------
DROP TABLE IF EXISTS `review_white_author`;
CREATE TABLE `review_white_author`  (
  `id` int NOT NULL,
  `site_key` varchar(16) CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL,
  `author_id` int NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8 COLLATE = utf8_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for sites
-- ----------------------------
DROP TABLE IF EXISTS `sites`;
CREATE TABLE `sites`  (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '网站ID',
  `web_name` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL COMMENT '网站名称',
  `web_key` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL COMMENT '网站标识字符串',
  `create_by` int NULL DEFAULT NULL,
  `create_time` datetime NULL DEFAULT NULL,
  `update_by` int NULL DEFAULT NULL,
  `update_time` datetime NULL DEFAULT NULL,
  `remark` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8 COLLATE = utf8_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for users
-- ----------------------------
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL,
  `permissions` enum('OWNER','ADMIN','PUBLIC') CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `locale` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `is_banned` bigint NULL DEFAULT NULL,
  `ban_end_time` datetime NULL DEFAULT NULL,
  `ban_start_time` datetime NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `user_id`(`user_id` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8 COLLATE = utf8_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for work
-- ----------------------------
DROP TABLE IF EXISTS `work`;
CREATE TABLE `work`  (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '作品归类表 主键',
  `name` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL,
  `description` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8 COLLATE = utf8_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for work_channel
-- ----------------------------
DROP TABLE IF EXISTS `work_channel`;
CREATE TABLE `work_channel`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `work_id` bigint NULL DEFAULT NULL,
  `channel_id` bigint NULL DEFAULT NULL COMMENT '频道ID',
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8 COLLATE = utf8_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for work_rules
-- ----------------------------
DROP TABLE IF EXISTS `work_rules`;
CREATE TABLE `work_rules`  (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '作品区分规则表 主键ID',
  `work_id` bigint NULL DEFAULT NULL COMMENT '绑定的作品类型',
  `name` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL COMMENT '作品名称类型',
  `description` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL COMMENT '作品类型描述',
  `search_text` varchar(255) CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL,
  `is_pattern` tinyint NULL DEFAULT NULL COMMENT '是否为正则表达式',
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8 COLLATE = utf8_general_ci ROW_FORMAT = Dynamic;

SET FOREIGN_KEY_CHECKS = 1;
