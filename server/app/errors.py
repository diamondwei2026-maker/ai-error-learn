"""统一错误码与业务异常。

业务失败统一返回 HTTP 200 + code（与既有识别接口一致）；
鉴权失败返回 HTTP 401 + code，便于前端统一续期。
"""

from __future__ import annotations

# 成功
CODE_OK = 0

# 用户域 2xxx
CODE_UNAUTHORIZED = 2001  # 未登录 / 缺少 token
CODE_TOKEN_INVALID = 2002  # 登录态失效
CODE_LOGIN_NOT_CONFIGURED = 2003  # 服务端未配置微信登录
CODE_WECHAT_CODE_INVALID = 2004  # 微信 code 无效
CODE_PARAM_INVALID = 2005  # 参数校验失败
CODE_AVATAR_INVALID = 2006  # 头像文件无效或过大
CODE_NICKNAME_RISK = 2007  # 昵称含违规内容（微信内容安全）

# 同步域 3xxx
CODE_SYNC_PAYLOAD_INVALID = 3001  # 同步数据格式错误
CODE_SYNC_CONTENT_RISK = 3002  # 错题题干/答案含违规内容（微信内容安全）


class ApiError(Exception):
    """业务异常：由全局异常处理器转换为统一信封响应。"""

    def __init__(self, code: int, message: str, http_status: int = 200) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


class TokenError(Exception):
    """JWT 解析/校验失败。"""

    def __init__(self, message: str = "登录态失效") -> None:
        super().__init__(message)
        self.message = message


class WechatLoginError(Exception):
    """微信 code2Session 失败。"""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
