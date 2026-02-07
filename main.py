'''
    金价实时监控 - 手机版
    version: 1.0
    提供浙商银行和民生银行金价实时监控 - 带提醒功能
    支持 Android/iOS
    2025年5月6日
'''

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.switch import Switch
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.utils import platform
from kivy.properties import StringProperty, BooleanProperty, ObjectProperty
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.core.audio import SoundLoader
from kivy.uix.widget import Widget
from kivy.metrics import dp
import threading
import json
import urllib.request
import urllib.parse
import time
import os

# ========== 注册中文字体 ==========
# 尝试多个可能的路径
font_paths = [
    'msyh.ttc',  # 同目录下
    'fonts/msyh.ttc',  # fonts子目录
    '/system/fonts/NotoSansCJK-Regular.ttc',  # 安卓系统
    '/system/fonts/DroidSansFallback.ttf',
]

CHINESE_FONT = 'Roboto'  # 默认字体

for font_path in font_paths:
    if os.path.exists(font_path):
        try:
            LabelBase.register(name='ChineseFont', fn_regular=font_path)
            CHINESE_FONT = 'ChineseFont'
            print(f"中文字体加载成功: {font_path}")
            break
        except Exception as e:
            print(f"字体加载失败 {font_path}: {e}")
            continue

if CHINESE_FONT == 'Roboto':
    print("警告：未找到中文字体，使用默认字体")
# ==================================

# 检测是否在 Android 上运行
IS_ANDROID = platform == 'android'

# 尝试导入 Android 特有的库
IS_ANDROID = platform == 'android'
if IS_ANDROID:
    try:
        from jnius import autoclass
        from android.runnable import run_on_ui_thread
        from android.permissions import request_permissions, Permission
        AndroidActivity = autoclass('org.kivy.android.PythonActivity')
        AndroidContext = autoclass('android.content.Context')
        AndroidNotificationBuilder = autoclass('android.app.Notification$Builder')
        AndroidNotificationManager = autoclass('android.app.NotificationManager')
        AndroidIntent = autoclass('android.content.Intent')
        AndroidPendingIntent = autoclass('android.app.PendingIntent')
        AndroidToast = autoclass('android.widget.Toast')
        ANDROID_AVAILABLE = True
    except:
        ANDROID_AVAILABLE = False
else:
    ANDROID_AVAILABLE = False

# URL配置
BANKS = {
    "浙商": {
        "url": "https://api.jdjygold.com/gw2/generic/jrm/h5/m/stdLatestPrice?productSku=1961543816",
        "color": [1, 0.843, 0, 1],  # 金色 #FFD700
        "method": "sku",
        "price_key": "price",
        "change_key": "upAndDownAmt"
    },
    "民生": {
        "url": "https://ms.jr.jd.com/gw2/generic/CreatorSer/newh5/m/getFirstRelatedProductInfo",
        "params": {"circleId": "13245", "invokeSource": 5, "productId": "21001001000001"},
        "color": [0.29, 0.565, 0.886, 1],  # 蓝色 #4A90E2
        "method": "product_id",
        "price_key": "minimumPriceValue",
        "change_key": "dayFluctuateNum"
    }
}

class StyledCard(BoxLayout):
    """自定义卡片组件"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = dp(15)
        self.spacing = dp(10)
        self.size_hint_y = None
        self.height = dp(120)
        
        with self.canvas.before:
            Color(0.15, 0.15, 0.15, 1)  # 深色背景
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])
            Color(0.3, 0.3, 0.3, 1)  # 边框
            self.border = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, dp(10)), width=1.5)
        
        self.bind(pos=self.update_rect, size=self.update_rect)
    
    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size
        self.border.rounded_rectangle = (self.x, self.y, self.width, self.height, dp(10))

class PriceDisplay(BoxLayout):
    """价格显示组件"""
    bank_name = StringProperty("")
    price = StringProperty("--")
    change = StringProperty("--")
    bank_color = ObjectProperty([1, 1, 1, 1])
    
    def __init__(self, bank_name, **kwargs):
        super().__init__(**kwargs)
        self.bank_name = bank_name
        self.bank_color = BANKS[bank_name]["color"]
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = dp(50)
        self.padding = [dp(10), dp(5)]
        
        # 银行名称
        name_label = Label(
            text=self.bank_name,
            font_size=dp(16),
            color=self.bank_color,
            size_hint_x=0.2,
            bold=True
        )
        
        # 价格
        self.price_label = Label(
            text="¥--",
            font_size=dp(24),
            color=[1, 0.843, 0, 1],
            size_hint_x=0.5,
            font_name='Roboto' if IS_ANDROID else 'Arial'
        )
        
        # 涨跌
        self.change_label = Label(
            text="--",
            font_size=dp(14),
            color=[0.88, 0.88, 0.88, 1],
            size_hint_x=0.3
        )
        
        self.add_widget(name_label)
        self.add_widget(self.price_label)
        self.add_widget(self.change_label)
    
    def update_price(self, price, change):
        self.price = str(price)
        self.change = str(change)
        self.price_label.text = f"¥{price}"
        
        # 更新涨跌颜色和符号
        try:
            change_val = float(change)
            if change_val > 0:
                self.change_label.color = [1, 0.42, 0.42, 1]  # 红色
                self.change_label.text = f"+{change}"
            elif change_val < 0:
                self.change_label.color = [0.31, 0.8, 0.77, 1]  # 绿色
                self.change_label.text = str(change)
            else:
                self.change_label.color = [0.88, 0.88, 0.88, 1]
                self.change_label.text = change
        except:
            self.change_label.text = change
            self.change_label.color = [0.88, 0.88, 0.88, 1]

class AlertSettingsPopup(Popup):
    """提醒设置弹窗"""
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.title = "提醒设置"
        self.size_hint = (0.9, 0.7)
        self.auto_dismiss = False
        
        layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(15))
        
        # 基准价格
        base_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50))
        base_layout.add_widget(Label(text="基准价格:", size_hint_x=0.3, color=[0.9, 0.9, 0.9, 1]))
        self.base_input = TextInput(
            text=str(app.alert_base_price) if app.alert_base_price else "",
            multiline=False,
            input_filter='float',
            background_color=[0.2, 0.2, 0.2, 1],
            foreground_color=[1, 1, 1, 1],
            cursor_color=[1, 0.843, 0, 1],
            padding=[dp(10), dp(10), 0, 0]
        )
        base_layout.add_widget(self.base_input)
        
        # 当前价格按钮
        current_btn = Button(
            text="当前",
            size_hint_x=0.2,
            background_color=[0.3, 0.3, 0.3, 1],
            color=[1, 1, 1, 1]
        )
        current_btn.bind(on_press=self.fill_current_price)
        base_layout.add_widget(current_btn)
        
        layout.add_widget(base_layout)
        
        # 涨幅设置
        up_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50))
        up_layout.add_widget(Label(text="涨多少(元):", size_hint_x=0.3, color=[0.9, 0.9, 0.9, 1]))
        self.up_input = TextInput(
            text=str(app.alert_up_amount) if app.alert_up_amount else "",
            multiline=False,
            input_filter='float',
            background_color=[0.2, 0.2, 0.2, 1],
            foreground_color=[1, 1, 1, 1]
        )
        up_layout.add_widget(self.up_input)
        layout.add_widget(up_layout)
        
        # 跌幅设置
        down_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50))
        down_layout.add_widget(Label(text="跌多少(元):", size_hint_x=0.3, color=[0.9, 0.9, 0.9, 1]))
        self.down_input = TextInput(
            text=str(app.alert_down_amount) if app.alert_down_amount else "",
            multiline=False,
            input_filter='float',
            background_color=[0.2, 0.2, 0.2, 1],
            foreground_color=[1, 1, 1, 1]
        )
        down_layout.add_widget(self.down_input)
        layout.add_widget(down_layout)
        
        # 启用开关
        switch_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50))
        switch_layout.add_widget(Label(text="启用提醒:", size_hint_x=0.3, color=[0.9, 0.9, 0.9, 1]))
        self.enabled_switch = Switch(active=app.alert_enabled)
        switch_layout.add_widget(self.enabled_switch)
        layout.add_widget(switch_layout)
        
        # 按钮区域
        btn_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50), spacing=dp(10))
        
        save_btn = Button(
            text="保存",
            background_color=[0.2, 0.6, 0.2, 1],
            color=[1, 1, 1, 1]
        )
        save_btn.bind(on_press=self.save_settings)
        
        cancel_btn = Button(
            text="取消",
            background_color=[0.6, 0.2, 0.2, 1],
            color=[1, 1, 1, 1]
        )
        cancel_btn.bind(on_press=self.dismiss)
        
        btn_layout.add_widget(save_btn)
        btn_layout.add_widget(cancel_btn)
        layout.add_widget(btn_layout)
        
        self.content = layout
    
    def fill_current_price(self, instance):
        current = self.app.get_current_zs_price()
        if current:
            self.base_input.text = str(current)
        else:
            self.app.show_toast("当前金价获取失败")
    
    def save_settings(self, instance):
        enabled = self.enabled_switch.active
        
        if enabled:
            try:
                base = float(self.base_input.text.strip())
                up = float(self.up_input.text.strip()) if self.up_input.text else 0
                down = float(self.down_input.text.strip()) if self.down_input.text else 0
                
                if base <= 0 or up < 0 or down < 0:
                    self.app.show_toast("价格必须大于0，涨跌金额必须>=0")
                    return
                
                self.app.alert_base_price = base
                self.app.alert_up_amount = up
                self.app.alert_down_amount = down
                self.app.alert_enabled = True
                
                self.app.show_toast(f"提醒已设置: 基准{base} 涨{up} 跌{down}")
                self.dismiss()
                
            except ValueError:
                self.app.show_toast("请输入有效的数字")
        else:
            self.app.alert_enabled = False
            self.app.alert_base_price = None
            self.app.alert_up_amount = None
            self.app.alert_down_amount = None
            self.app.show_toast("提醒已关闭")
            self.dismiss()

class GoldPriceApp(App):
    alert_enabled = BooleanProperty(False)
    alert_base_price = ObjectProperty(None)
    alert_up_amount = ObjectProperty(None)
    alert_down_amount = ObjectProperty(None)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.prices = {name: {"price": "--", "change": "--"} for name in BANKS}
        self.running = True
        self.price_displays = {}
        
        # 语音相关
        self.tts_engine = None
        self.init_tts()
        
        # 后台运行
        self.background_thread = None
    
    def init_tts(self):
        """初始化语音引擎"""
        if IS_ANDROID and ANDROID_AVAILABLE:
            try:
                self.tts_engine = autoclass('android.speech.tts.TextToSpeech')(AndroidActivity.mActivity, None)
            except Exception as e:
                print(f"TTS初始化失败: {e}")
    
    def build(self):
        # 设置窗口背景色（深色主题）
        Window.clearcolor = (0.1, 0.1, 0.1, 1)
        
        # 主布局
        root = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        
        # 标题栏
        title_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(60))
        title_label = Label(
            text='[b]金价监控[/b]',
            markup=True,
            font_size=dp(24),
            color=[1, 0.843, 0, 1],
            font_name=CHINESE_FONT
        )
        title_box.add_widget(title_label)
        root.add_widget(title_box)
        
        # 价格卡片区域
        cards_layout = BoxLayout(orientation='vertical', spacing=dp(15), padding=[dp(5), dp(10)])
        
        # 浙商银行卡片
        zs_card = StyledCard()
        zs_title = Label(
            text='[b]浙商银行[/b]',
            markup=True,
            font_size=dp(18),
            color=BANKS["浙商"]["color"],
            size_hint_y=None,
            height=dp(30)
        )
        zs_card.add_widget(zs_title)
        
        self.zs_display = PriceDisplay("浙商")
        zs_card.add_widget(self.zs_display)
        self.price_displays["浙商"] = self.zs_display
        
        cards_layout.add_widget(zs_card)
        
        # 民生银行卡片
        ms_card = StyledCard()
        ms_title = Label(
            text='[b]民生银行[/b]',
            markup=True,
            font_size=dp(18),
            color=BANKS["民生"]["color"],
            size_hint_y=None,
            height=dp(30)
        )
        ms_card.add_widget(ms_title)
        
        self.ms_display = PriceDisplay("民生")
        ms_card.add_widget(self.ms_display)
        self.price_displays["民生"] = self.ms_display
        
        cards_layout.add_widget(ms_card)
        
        root.add_widget(cards_layout)
        
        # 按钮区域
        btn_layout = GridLayout(cols=2, size_hint_y=None, height=dp(120), spacing=dp(10), padding=[dp(10), dp(20)])
        
        # 提醒设置按钮
        alert_btn = Button(
            text='[b]提醒设置[/b]',
            markup=True,
            font_size=dp(16),
            background_color=[0.2, 0.5, 0.8, 1],
            color=[1, 1, 1, 1]
        )
        alert_btn.bind(on_press=self.show_alert_settings)
        btn_layout.add_widget(alert_btn)
        
        # 刷新按钮
        refresh_btn = Button(
            text='[b]立即刷新[/b]',
            markup=True,
            font_size=dp(16),
            background_color=[0.2, 0.6, 0.3, 1],
            color=[1, 1, 1, 1]
        )
        refresh_btn.bind(on_press=self.manual_refresh)
        btn_layout.add_widget(refresh_btn)
        
        # 语音测试按钮
        test_btn = Button(
            text='[b]语音测试[/b]',
            markup=True,
            font_size=dp(16),
            background_color=[0.6, 0.4, 0.1, 1],
            color=[1, 1, 1, 1]
        )
        test_btn.bind(on_press=self.test_voice)
        btn_layout.add_widget(test_btn)
        
        # 后台运行开关
        bg_layout = BoxLayout(orientation='horizontal')
        bg_label = Label(text='后台运行', color=[0.9, 0.9, 0.9, 1], font_size=dp(14))
        self.bg_switch = Switch(active=False)
        self.bg_switch.bind(active=self.toggle_background)
        bg_layout.add_widget(bg_label)
        bg_layout.add_widget(self.bg_switch)
        btn_layout.add_widget(bg_layout)
        
        root.add_widget(btn_layout)
        
        # 状态栏
        self.status_label = Label(
            text='正在连接...',
            font_size=dp(12),
            color=[0.6, 0.6, 0.6, 1],
            size_hint_y=None,
            height=dp(30)
        )
        root.add_widget(self.status_label)
        
        # 启动数据获取线程
        self.start_data_thread()
        
        return root
    
    def start_data_thread(self):
        """启动后台数据获取线程"""
        thread = threading.Thread(target=self.fetch_data_loop, daemon=True)
        thread.start()
    
    def fetch_data_loop(self):
        """数据获取循环"""
        while self.running:
            self.update_prices()
            time.sleep(3)  # 每3秒更新一次
    
    def update_prices(self):
        """更新价格数据"""
        for bank_name, config in BANKS.items():
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Linux; Android 10; Mobile) AppleWebKit/537.36',
                    'Accept': 'application/json',
                    'Referer': 'https://jdjygold.com/'
                }
                
                if config.get('method') == 'product_id':
                    req_data = json.dumps(config['params'])
                    encoded_data = urllib.parse.quote(req_data)
                    full_url = f"{config['url']}?reqData={encoded_data}"
                    
                    req = urllib.request.Request(full_url, headers=headers)
                    with urllib.request.urlopen(req, timeout=10) as response:
                        data = json.loads(response.read().decode('utf-8'))
                    
                    result_data = data.get('resultData', {})
                    data_obj = result_data.get('data', {})
                    
                    price = data_obj.get(config['price_key'], '--')
                    change = data_obj.get(config['change_key'], '--')
                    
                else:
                    req = urllib.request.Request(config["url"], headers=headers)
                    with urllib.request.urlopen(req, timeout=10) as response:
                        data = json.loads(response.read().decode('utf-8'))
                    
                    result_data = data.get('resultData', {})
                    if result_data.get('status') == 'FAIL':
                        continue
                    
                    datas = result_data.get('datas', {})
                    price = datas.get(config['price_key'], '--')
                    change = datas.get(config['change_key'], '--')
                
                # 更新数据
                self.prices[bank_name]["price"] = str(price)
                self.prices[bank_name]["change"] = str(change)
                
                # 更新UI
                Clock.schedule_once(lambda dt, bn=bank_name, p=price, c=change: 
                    self.update_ui(bn, p, c), 0)
                
                # 检查提醒（仅浙商银行）
                if bank_name == "浙商":
                    self.check_alert(price)
                
            except Exception as e:
                print(f"{bank_name} 获取失败: {e}")
                Clock.schedule_once(lambda dt, msg=f"{bank_name}连接失败": 
                    self.update_status(msg), 0)
    
    def update_ui(self, bank_name, price, change):
        """更新UI"""
        if bank_name in self.price_displays:
            self.price_displays[bank_name].update_price(price, change)
        self.status_label.text = f"最后更新: {time.strftime('%H:%M:%S')}"
        self.status_label.color = [0.4, 0.8, 0.4, 1]
    
    def update_status(self, message):
        """更新状态信息"""
        self.status_label.text = message
        self.status_label.color = [0.8, 0.4, 0.4, 1]
    
    def get_current_zs_price(self):
        """获取当前浙商银行价格"""
        try:
            price = self.prices["浙商"]["price"]
            if price and price != "--" and price != "失败":
                return float(price)
        except:
            pass
        return None
    
    def check_alert(self, current_price):
        """检查价格提醒"""
        if not self.alert_enabled or not self.alert_base_price:
            return
        
        try:
            current = float(current_price)
            base = float(self.alert_base_price)
            up_limit = float(self.alert_up_amount) if self.alert_up_amount else 0
            down_limit = float(self.alert_down_amount) if self.alert_down_amount else 0
            
            upper_limit = base + up_limit
            lower_limit = base - down_limit
            
            triggered = False
            direction = ""
            
            if current >= upper_limit:
                direction = "涨了"
                triggered = True
                self.alert_base_price = current
            
            elif current <= lower_limit:
                direction = "跌了"
                triggered = True
                self.alert_base_price = current
            
            if triggered:
                price_str = str(current_price)
                message = f"{direction}，现在{price_str}元"
                
                # 显示通知
                Clock.schedule_once(lambda dt: self.show_notification("金价提醒", message), 0)
                
                # 语音播报
                self.speak_price(direction, price_str)
                
        except (ValueError, TypeError):
            pass
    
    def show_notification(self, title, message):
        """显示通知（Android原生通知或弹窗）"""
        if IS_ANDROID and ANDROID_AVAILABLE:
            try:
                self.send_android_notification(title, message)
            except Exception as e:
                print(f"Android通知失败: {e}")
                self.show_popup(title, message)
        else:
            self.show_popup(title, message)
    
    def send_android_notification(self, title, message):
        """发送Android原生通知"""
        if not ANDROID_AVAILABLE:
            return
        
        try:
            context = AndroidActivity.mActivity.getApplicationContext()
            notification_manager = context.getSystemService(AndroidContext.NOTIFICATION_SERVICE)
            
            # 创建通知
            builder = AndroidNotificationBuilder(context)
            builder.setContentTitle(title)
            builder.setContentText(message)
            builder.setSmallIcon(context.getApplicationInfo().icon)
            builder.setAutoCancel(True)
            
            # 创建点击意图
            intent = AndroidIntent(context, AndroidActivity)
            pending_intent = AndroidPendingIntent.getActivity(context, 0, intent, 
                                                             AndroidPendingIntent.FLAG_IMMUTABLE)
            builder.setContentIntent(pending_intent)
            
            # 发送通知
            notification_manager.notify(1, builder.build())
        except Exception as e:
            print(f"发送通知错误: {e}")
    
    def show_popup(self, title, message):
        """显示弹窗通知"""
        popup = Popup(
            title=title,
            content=Label(text=message, font_size=dp(16)),
            size_hint=(0.8, 0.3),
            auto_dismiss=True
        )
        popup.open()
        
        # 3秒后自动关闭
        Clock.schedule_once(lambda dt: popup.dismiss(), 3)
    
    def speak_price(self, direction, price_str):
        """语音播报价格"""
        # 将数字转换为中文读法
        number_map = {
            '0': '零', '1': '一', '2': '二', '3': '三', '4': '四',
            '5': '五', '6': '六', '7': '七', '8': '八', '9': '九', '.': '点'
        }
        price_chinese = ''.join([number_map.get(c, c) for c in price_str])
        
        text = f"{direction}，现在{price_chinese}元"
        
        if IS_ANDROID and ANDROID_AVAILABLE and self.tts_engine:
            try:
                self.tts_engine.speak(text, None, None)
            except Exception as e:
                print(f"TTS失败: {e}")
                self.show_toast(text)
        else:
            # 非Android平台显示Toast或弹窗
            self.show_toast(text)
    
    def show_toast(self, message):
        """显示Toast消息"""
        if IS_ANDROID and ANDROID_AVAILABLE:
            try:
                AndroidToast.makeText(AndroidActivity.mActivity, message, 
                                     AndroidToast.LENGTH_LONG).show()
            except:
                self.show_popup("提示", message)
        else:
            self.show_popup("提示", message)
    
    def show_alert_settings(self, instance):
        """显示提醒设置"""
        popup = AlertSettingsPopup(self)
        popup.open()
    
    def manual_refresh(self, instance):
        """手动刷新"""
        self.status_label.text = "正在刷新..."
        threading.Thread(target=self.update_prices, daemon=True).start()
    
    def test_voice(self, instance):
        """测试语音"""
        self.speak_price("测试", "778.50")
        self.show_toast("语音测试")
    
    def toggle_background(self, instance, value):
        """切换后台运行"""
        if value:
            self.show_toast("后台运行已开启（应用保持运行）")
            # 防止屏幕关闭
            if IS_ANDROID:
                try:
                    from android import AndroidService
                    service = AndroidService('GoldPriceService', '金价监控运行中...')
                    service.start('服务正在运行')
                except:
                    pass
        else:
            self.show_toast("后台运行已关闭")
    
    def on_pause(self):
        """应用暂停时（后台运行）"""
        if self.alert_enabled:
            return True  # 保持运行
        return False
    
    def on_resume(self):
        """应用恢复时"""
        pass
    
    def on_stop(self):
        """应用停止时"""
        self.running = False
        if self.tts_engine:
            try:
                self.tts_engine.stop()
                self.tts_engine.shutdown()
            except:
                pass

# 构建应用
if __name__ == '__main__':
    # 请求Android权限
    if IS_ANDROID:
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.INTERNET,
                Permission.FOREGROUND_SERVICE,
                Permission.POST_NOTIFICATIONS
            ])
        except:
            pass
    
    GoldPriceApp().run()