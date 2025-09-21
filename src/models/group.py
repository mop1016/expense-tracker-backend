from datetime import datetime
import json

class Group:
    def __init__(self, db_connection):
        self.db = db_connection
        self.create_tables()
    
    def create_tables(self):
        """創建群組相關表格"""
        cursor = self.db.cursor()
        
        # 群組表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                created_by INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                settings TEXT DEFAULT '{}',
                FOREIGN KEY (created_by) REFERENCES users (id)
            )
        ''')
        
        # 群組成員表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS group_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                role VARCHAR(20) DEFAULT 'member',
                status VARCHAR(20) DEFAULT 'active',
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                invited_by INTEGER,
                FOREIGN KEY (group_id) REFERENCES groups (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (invited_by) REFERENCES users (id),
                UNIQUE(group_id, user_id)
            )
        ''')
        
        # 群組邀請表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS group_invitations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                inviter_id INTEGER NOT NULL,
                invitee_id INTEGER NOT NULL,
                status VARCHAR(20) DEFAULT 'pending',
                message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                responded_at TIMESTAMP,
                FOREIGN KEY (group_id) REFERENCES groups (id) ON DELETE CASCADE,
                FOREIGN KEY (inviter_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (invitee_id) REFERENCES users (id) ON DELETE CASCADE,
                UNIQUE(group_id, invitee_id, status)
            )
        ''')
        
        self.db.commit()
    
    def create_group(self, name, description, created_by, member_names=None):
        """創建群組"""
        try:
            # 更寬鬆的群組名稱驗證
            if not name or not name.strip():
                return {"success": False, "message": "群組名稱不能為空"}
            
            # 檢查群組名稱長度（支援中文字符）
            name_stripped = name.strip()
            if len(name_stripped) < 1:
                return {"success": False, "message": "群組名稱不能為空"}
            
            # 檢查群組名稱長度上限
            if len(name_stripped) > 50:
                return {"success": False, "message": "群組名稱不能超過50個字符"}
            
            cursor = self.db.cursor()
            
            # 檢查群組名稱是否已存在（同一創建者）
            cursor.execute('''
                SELECT id FROM groups 
                WHERE name = ? AND created_by = ? AND is_active = 1
            ''', (name_stripped, created_by))
            
            if cursor.fetchone():
                return {"success": False, "message": "您已經有同名的群組"}
            
            # 創建群組
            cursor.execute('''
                INSERT INTO groups (name, description, created_by, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (name_stripped, description or '', created_by, datetime.now(), datetime.now()))
            
            group_id = cursor.lastrowid
            
            # 添加創建者為管理員
            cursor.execute('''
                INSERT INTO group_members (group_id, user_id, role, status, joined_at)
                VALUES (?, ?, 'admin', 'active', ?)
            ''', (group_id, created_by, datetime.now()))
            
            # 如果提供了成員名單，發送邀請
            invited_users = []
            if member_names:
                # 解析成員名單（支援逗號分隔的姓名）
                names = [name.strip() for name in member_names.split(',') if name.strip()]
                
                for name in names:
                    # 搜索用戶 - 使用模糊匹配和去除空格
                    name_trimmed = name.strip()
                    cursor.execute('''
                        SELECT id, full_name, username FROM users 
                        WHERE (full_name = ? OR full_name LIKE ?) AND is_active = 1
                        LIMIT 1
                    ''', (name_trimmed, f'%{name_trimmed}%'))
                    
                    user = cursor.fetchone()
                    if user and user[0] != created_by:  # 不邀請自己
                        # 檢查是否已經是群組成員
                        cursor.execute('''
                            SELECT id FROM group_members 
                            WHERE group_id = ? AND user_id = ? AND status = 'active'
                        ''', (group_id, user[0]))
                        
                        if not cursor.fetchone():  # 不是現有成員
                            # 檢查是否已有待處理邀請
                            cursor.execute('''
                                SELECT id FROM group_invitations 
                                WHERE group_id = ? AND invitee_id = ? AND status = 'pending'
                            ''', (group_id, user[0]))
                            
                            if not cursor.fetchone():  # 沒有待處理邀請
                                # 發送邀請
                                try:
                                    cursor.execute('''
                                        INSERT INTO group_invitations (group_id, inviter_id, invitee_id, status, created_at)
                                        VALUES (?, ?, ?, 'pending', ?)
                                    ''', (group_id, created_by, user[0], datetime.now()))
                                    
                                    invited_users.append({
                                        "id": user[0],
                                        "full_name": user[1],
                                        "username": user[2]
                                    })
                                except Exception as e:
                                    pass
                    else:
                        pass
            
            self.db.commit()
            
            # 獲取完整的群組信息
            group_info = self.get_group_by_id(group_id)
            
            return {
                "success": True,
                "message": f"群組創建成功，已邀請 {len(invited_users)} 位成員",
                "group": group_info,
                "invited_users": invited_users
            }
            
        except Exception as e:
            return {"success": False, "message": f"創建群組失敗: {str(e)}"}
    
    def get_group_by_id(self, group_id):
        """根據ID獲取群組信息"""
        try:
            cursor = self.db.cursor()
            
            # 獲取群組基本信息
            cursor.execute('''
                SELECT g.id, g.name, g.description, g.created_by, g.created_at, g.updated_at,
                       u.full_name as creator_name, u.username as creator_username
                FROM groups g
                JOIN users u ON g.created_by = u.id
                WHERE g.id = ? AND g.is_active = 1
            ''', (group_id,))
            
            group = cursor.fetchone()
            if not group:
                return None
            
            # 獲取成員信息
            cursor.execute('''
                SELECT gm.user_id, gm.role, gm.status, gm.joined_at,
                       u.full_name, u.username, u.avatar_url
                FROM group_members gm
                JOIN users u ON gm.user_id = u.id
                WHERE gm.group_id = ? AND gm.status = 'active'
                ORDER BY gm.role DESC, gm.joined_at ASC
            ''', (group_id,))
            
            members = cursor.fetchall()
            
            # 獲取待處理邀請數量
            cursor.execute('''
                SELECT COUNT(*) FROM group_invitations 
                WHERE group_id = ? AND status = 'pending'
            ''', (group_id,))
            
            pending_invitations = cursor.fetchone()[0]
            
            return {
                "id": group[0],
                "name": group[1],
                "description": group[2],
                "created_by": group[3],
                "created_at": group[4],
                "updated_at": group[5],
                "creator_name": group[6],
                "creator_username": group[7],
                "member_count": len(members),
                "pending_invitations": pending_invitations,
                "members": [
                    {
                        "user_id": member[0],
                        "role": member[1],
                        "status": member[2],
                        "joined_at": member[3],
                        "full_name": member[4],
                        "username": member[5],
                        "avatar_url": member[6]
                    }
                    for member in members
                ]
            }
            
        except Exception as e:
            return None
    
    def get_user_groups(self, user_id):
        """獲取用戶所屬的群組列表"""
        try:
            cursor = self.db.cursor()
            cursor.execute('''
                SELECT g.id, g.name, g.description, g.created_by, g.created_at,
                       gm.role, gm.joined_at,
                       (SELECT COUNT(*) FROM group_members WHERE group_id = g.id AND status = 'active') as member_count
                FROM groups g
                JOIN group_members gm ON g.id = gm.group_id
                WHERE gm.user_id = ? AND gm.status = 'active' AND g.is_active = 1
                ORDER BY gm.role DESC, g.created_at DESC
            ''', (user_id,))
            
            groups = cursor.fetchall()
            
            return [
                {
                    "id": group[0],
                    "name": group[1],
                    "description": group[2],
                    "created_by": group[3],
                    "created_at": group[4],
                    "user_role": group[5],
                    "joined_at": group[6],
                    "member_count": group[7]
                }
                for group in groups
            ]
            
        except Exception as e:
            return []
    
    def get_group_members(self, group_id, user_id):
        """獲取群組成員列表"""
        try:
            cursor = self.db.cursor()
            
            # 檢查用戶是否是群組成員
            cursor.execute('''
                SELECT role FROM group_members 
                WHERE group_id = ? AND user_id = ? AND status = 'active'
            ''', (group_id, user_id))
            
            user_member = cursor.fetchone()
            if not user_member:
                return {"success": False, "message": "您不是該群組成員"}
            
            # 獲取群組成員列表
            cursor.execute('''
                SELECT gm.user_id, gm.role, gm.joined_at,
                       u.username, u.full_name, u.email, u.avatar_url
                FROM group_members gm
                JOIN users u ON gm.user_id = u.id
                WHERE gm.group_id = ? AND gm.status = 'active'
                ORDER BY gm.role DESC, gm.joined_at ASC
            ''', (group_id,))
            
            members = cursor.fetchall()
            
            return {
                "success": True,
                "members": [
                    {
                        "user_id": member[0],
                        "role": member[1],
                        "joined_at": member[2],
                        "username": member[3],
                        "full_name": member[4],
                        "email": member[5],
                        "avatar_url": member[6]
                    }
                    for member in members
                ]
            }
            
        except Exception as e:
            return {"success": False, "message": f"獲取群組成員失敗: {str(e)}"}
    
    def delete_group(self, group_id, user_id):
        """刪除群組"""
        try:
            cursor = self.db.cursor()
            
            # 檢查用戶是否是群組管理員
            cursor.execute('''
                SELECT role FROM group_members 
                WHERE group_id = ? AND user_id = ? AND status = 'active'
            ''', (group_id, user_id))
            
            user_role = cursor.fetchone()
            if not user_role or user_role[0] != 'admin':
                return {"success": False, "message": "只有群組管理員可以刪除群組"}
            
            # 檢查群組是否有關聯的交易記錄
            cursor.execute('''
                SELECT COUNT(*) FROM transactions WHERE group_id = ?
            ''', (group_id,))
            
            transaction_count = cursor.fetchone()[0]
            if transaction_count > 0:
                return {"success": False, "message": f"無法刪除群組，還有 {transaction_count} 筆交易記錄關聯到此群組"}
            
            # 刪除群組相關資料
            # 1. 刪除群組邀請
            cursor.execute('DELETE FROM group_invitations WHERE group_id = ?', (group_id,))
            
            # 2. 刪除群組成員
            cursor.execute('DELETE FROM group_members WHERE group_id = ?', (group_id,))
            
            # 3. 刪除群組
            cursor.execute('DELETE FROM groups WHERE id = ?', (group_id,))
            
            self.db.commit()
            
            return {"success": True, "message": "群組已成功刪除"}
            
        except Exception as e:
            return {"success": False, "message": f"刪除群組失敗: {str(e)}"}
    
    def invite_user_to_group(self, group_id, inviter_id, invitee_id, message=None):
        """邀請用戶加入群組"""
        try:
            cursor = self.db.cursor()
            
            # 檢查邀請者是否有權限
            cursor.execute('''
                SELECT role FROM group_members 
                WHERE group_id = ? AND user_id = ? AND status = 'active'
            ''', (group_id, inviter_id))
            
            inviter = cursor.fetchone()
            if not inviter or inviter[0] not in ['admin', 'moderator']:
                return {"success": False, "message": "您沒有邀請權限"}
            
            # 檢查被邀請者是否已經是成員
            cursor.execute('''
                SELECT status FROM group_members 
                WHERE group_id = ? AND user_id = ?
            ''', (group_id, invitee_id))
            
            existing_member = cursor.fetchone()
            if existing_member:
                if existing_member[0] == 'active':
                    return {"success": False, "message": "該用戶已經是群組成員"}
                elif existing_member[0] == 'pending':
                    return {"success": False, "message": "該用戶已有待處理的邀請"}
            
            # 檢查是否已有待處理邀請
            cursor.execute('''
                SELECT id FROM group_invitations 
                WHERE group_id = ? AND invitee_id = ? AND status = 'pending'
            ''', (group_id, invitee_id))
            
            if cursor.fetchone():
                return {"success": False, "message": "該用戶已有待處理的邀請"}
            
            # 創建邀請
            cursor.execute('''
                INSERT INTO group_invitations (group_id, inviter_id, invitee_id, message, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (group_id, inviter_id, invitee_id, message, datetime.now()))
            
            self.db.commit()
            
            return {"success": True, "message": "邀請已發送"}
            
        except Exception as e:
            return {"success": False, "message": f"發送邀請失敗: {str(e)}"}
    
    def respond_to_invitation(self, invitation_id, user_id, accept=True):
        """回應群組邀請"""
        try:
            cursor = self.db.cursor()
            
            # 獲取邀請信息
            cursor.execute('''
                SELECT group_id, invitee_id, status FROM group_invitations 
                WHERE id = ? AND invitee_id = ?
            ''', (invitation_id, user_id))
            
            invitation = cursor.fetchone()
            if not invitation:
                return {"success": False, "message": "邀請不存在"}
            
            if invitation[2] != 'pending':
                return {"success": False, "message": "邀請已處理"}
            
            group_id = invitation[0]
            status = 'accepted' if accept else 'declined'
            
            # 更新邀請狀態
            cursor.execute('''
                UPDATE group_invitations 
                SET status = ?, responded_at = ?
                WHERE id = ?
            ''', (status, datetime.now(), invitation_id))
            
            # 如果接受邀請，添加為群組成員
            if accept:
                cursor.execute('''
                    INSERT OR REPLACE INTO group_members (group_id, user_id, role, status, joined_at)
                    VALUES (?, ?, 'member', 'active', ?)
                ''', (group_id, user_id, datetime.now()))
            
            self.db.commit()
            
            message = "已加入群組" if accept else "已拒絕邀請"
            return {"success": True, "message": message}
            
        except Exception as e:
            return {"success": False, "message": f"處理邀請失敗: {str(e)}"}
    
    def get_user_invitations(self, user_id):
        """獲取用戶的群組邀請"""
        try:
            cursor = self.db.cursor()
            cursor.execute('''
                SELECT gi.id, gi.group_id, gi.message, gi.created_at,
                       g.name as group_name, g.description as group_description,
                       u.full_name as inviter_name, u.username as inviter_username
                FROM group_invitations gi
                JOIN groups g ON gi.group_id = g.id
                JOIN users u ON gi.inviter_id = u.id
                WHERE gi.invitee_id = ? AND gi.status = 'pending'
                ORDER BY gi.created_at DESC
            ''', (user_id,))
            
            invitations = cursor.fetchall()
            
            return [
                {
                    "id": inv[0],
                    "group_id": inv[1],
                    "message": inv[2],
                    "created_at": inv[3],
                    "group_name": inv[4],
                    "group_description": inv[5],
                    "inviter_name": inv[6],
                    "inviter_username": inv[7]
                }
                for inv in invitations
            ]
            
        except Exception as e:
            return []
    
    def remove_member(self, group_id, admin_id, member_id):
        """移除群組成員"""
        try:
            cursor = self.db.cursor()
            
            # 檢查操作者權限
            cursor.execute('''
                SELECT role FROM group_members 
                WHERE group_id = ? AND user_id = ? AND status = 'active'
            ''', (group_id, admin_id))
            
            admin = cursor.fetchone()
            if not admin or admin[0] not in ['admin']:
                return {"success": False, "message": "您沒有移除成員的權限"}
            
            # 不能移除自己
            if admin_id == member_id:
                return {"success": False, "message": "不能移除自己"}
            
            # 檢查被移除者是否是成員
            cursor.execute('''
                SELECT role FROM group_members 
                WHERE group_id = ? AND user_id = ? AND status = 'active'
            ''', (group_id, member_id))
            
            member = cursor.fetchone()
            if not member:
                return {"success": False, "message": "該用戶不是群組成員"}
            
            # 移除成員
            cursor.execute('''
                UPDATE group_members 
                SET status = 'removed'
                WHERE group_id = ? AND user_id = ?
            ''', (group_id, member_id))
            
            self.db.commit()
            
            return {"success": True, "message": "成員已移除"}
            
        except Exception as e:
            return {"success": False, "message": f"移除成員失敗: {str(e)}"}
    
    def leave_group(self, group_id, user_id):
        """離開群組"""
        try:
            cursor = self.db.cursor()
            
            # 檢查是否是群組成員
            cursor.execute('''
                SELECT role FROM group_members 
                WHERE group_id = ? AND user_id = ? AND status = 'active'
            ''', (group_id, user_id))
            
            member = cursor.fetchone()
            if not member:
                return {"success": False, "message": "您不是該群組成員"}
            
            # 如果是管理員，檢查是否還有其他管理員
            if member[0] == 'admin':
                cursor.execute('''
                    SELECT COUNT(*) FROM group_members 
                    WHERE group_id = ? AND role = 'admin' AND status = 'active'
                ''', (group_id,))
                
                admin_count = cursor.fetchone()[0]
                if admin_count <= 1:
                    return {"success": False, "message": "您是唯一的管理員，請先指定其他管理員或刪除群組"}
            
            # 離開群組
            cursor.execute('''
                UPDATE group_members 
                SET status = 'left'
                WHERE group_id = ? AND user_id = ?
            ''', (group_id, user_id))
            
            self.db.commit()
            
            return {"success": True, "message": "已離開群組"}
            
        except Exception as e:
            return {"success": False, "message": f"離開群組失敗: {str(e)}"}
    
    def delete_group(self, group_id, user_id):
        """刪除群組"""
        try:
            cursor = self.db.cursor()
            
            # 檢查是否是群組創建者
            cursor.execute('''
                SELECT created_by FROM groups 
                WHERE id = ? AND is_active = 1
            ''', (group_id,))
            
            group = cursor.fetchone()
            if not group:
                return {"success": False, "message": "群組不存在"}
            
            if group[0] != user_id:
                return {"success": False, "message": "只有群組創建者可以刪除群組"}
            
            # 軟刪除群組
            cursor.execute('''
                UPDATE groups 
                SET is_active = 0, updated_at = ?
                WHERE id = ?
            ''', (datetime.now(), group_id))
            
            # 移除所有成員
            cursor.execute('''
                UPDATE group_members 
                SET status = 'removed'
                WHERE group_id = ?
            ''', (group_id,))
            
            # 取消所有待處理邀請
            cursor.execute('''
                UPDATE group_invitations 
                SET status = 'cancelled'
                WHERE group_id = ? AND status = 'pending'
            ''', (group_id,))
            
            self.db.commit()
            
            return {"success": True, "message": "群組已刪除"}
            
        except Exception as e:
            return {"success": False, "message": f"刪除群組失敗: {str(e)}"}

