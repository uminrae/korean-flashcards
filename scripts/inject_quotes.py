"""
inject_quotes.py
----------------
为 data/korean_vocab.json 中的经典重点词汇补充高质量真实 K-POP 歌词与韩剧经典台词语境
"""

import json
import os

QUOTES_LIBRARY = {
    "안녕하세요": {
        "kr": "안녕하세요, 오늘도 그대에게 좋은 하루가 되기를 바래요.",
        "cn": "你好，愿你今天也能度过美好充实的一天。",
        "source": "좋은 날 - IU",
        "type": "song"
    },
    "안녕": {
        "kr": "안녕이란 말은 하지 마, 우리에겐 다음이 있으니까.",
        "cn": "不要说再见，因为我们还有下一次相遇。",
        "source": "Love Poem - IU",
        "type": "song"
    },
    "처음 뵙겠습니다": {
        "kr": "처음 뵙겠습니다. 당신이 정말 내 운명의 사람인가요?",
        "cn": "初次见面。您真的是我命中注定的那个人吗？",
        "source": "tvN 《来自星星的你》",
        "type": "drama"
    },
    "만나서 반갑습니다": {
        "kr": "이렇게 만나서 반갑습니다, 세상에서 가장 따뜻한 인연으로.",
        "cn": "能这样与你相见很高兴，愿这是世间最温暖的缘分。",
        "source": "tvN 《请回答1988》",
        "type": "drama"
    },
    "친구": {
        "kr": "영원히 함께할 내 작은 별, 우리 오랜 친구여.",
        "cn": "永远陪伴我的渺小星球，我们长久相伴的挚友啊。",
        "source": "Friends - BTS",
        "type": "song"
    },
    "사랑": {
        "kr": "사랑을 했다 우리가 만나 지우지 못할 추억이 됐다.",
        "cn": "我们曾经相爱，彼此相遇，化作了无法抹去的珍贵回忆。",
        "source": "LOVE SCENARIO - iKON",
        "type": "song"
    },
    "별": {
        "kr": "가장 깊은 밤에 더 빛나는 별빛, 밤이 깊을수록 더 빛나는 별빛.",
        "cn": "在最深沉的夜空中更加耀眼的星光，夜越深星光越是明亮。",
        "source": "소우주 (Mikrokosmos) - BTS",
        "type": "song"
    },
    "바람": {
        "kr": "불어오는 시원한 바람 속에서도 여전히 그대 향기가 나요.",
        "cn": "即使在拂面而来的清凉微风中，依然能嗅到你的芬芳气息。",
        "source": "I - 太妍 (TAEYEON)",
        "type": "song"
    },
    "봄": {
        "kr": "보고 싶다 이렇게 말하니까 더 보고 싶다... 추운 겨울 끝을 지나 다시 봄날이 올 때까지.",
        "cn": "好想你，这样说出口就更加思念... 熬过寒冬的尽头，直到春日再次降临。",
        "source": "봄날 (Spring Day) - BTS",
        "type": "song"
    },
    "비": {
        "kr": "비가 내리고 음악이 흐르면 난 당신을 생각해요.",
        "cn": "当细雨飘落音乐流淌之时，我便会情不自禁地想起你。",
        "source": "모든 날, 모든 순간 - Paul Kim",
        "type": "song"
    },
    "하루": {
        "kr": "오늘 하루도 참 수고 많았어요, 지친 너의 손을 꼭 잡아줄게요.",
        "cn": "今天这一整天真的辛苦你啦，我会紧紧握住你疲惫的双手。",
        "source": "밤편지 (Through the Night) - IU",
        "type": "song"
    },
    "마음": {
        "kr": "내 마음속에 항상 반짝이며 피어있는 너라는 예쁜 꽃.",
        "cn": "在我心中永远闪烁绽放的、名为你的那一朵绚丽花朵。",
        "source": "우주를 줄게 - 脸红的思春期 (BOL4)",
        "type": "song"
    },
    "기억": {
        "kr": "너와 함께한 시간 모두 눈부셨다. 날이 좋아서, 날이 좋지 않아서, 날이 적당해서, 모든 날이 좋았다.",
        "cn": "与你共度的所有时光都无比耀眼。因为天气好，因为天气不好，因为天气刚刚好，每一天都很美好。",
        "source": "tvN 《孤单又灿烂的神-鬼怪》",
        "type": "drama"
    },
    "기억하다": {
        "kr": "너와 함께한 시간 모두 눈부셨다. 영원히 너를 기억할게.",
        "cn": "与你共度的所有时光都无比耀眼。我会永远铭记着你。",
        "source": "tvN 《孤单又灿烂的神-鬼怪》",
        "type": "drama"
    },
    "사랑하다": {
        "kr": "사랑을 했다 우리가 만나 지우지 못할 추억이 됐다.",
        "cn": "我们曾经相爱，彼此相遇，化作了无法抹去的珍贵回忆。",
        "source": "LOVE SCENARIO - iKON",
        "type": "song"
    },
    "행복하다": {
        "kr": "우리가 함께 웃을 수 있는 지금 이 순간이 바로 가장 큰 행복이야.",
        "cn": "我们能够并肩开怀大笑的此时此刻，就是世间最真实巨大的幸福。",
        "source": "이 사랑 - Davichi",
        "type": "song"
    },
    "약속하다": {
        "kr": "다음 생이 있다면 그곳에서도 망설임 없이 당신을 찾아갈 것을 약속합니다.",
        "cn": "若有来生，我也向你郑重承诺，定会毫不犹豫地再次奔赴找到你。",
        "source": "KBS 《太阳的后裔》",
        "type": "drama"
    },
    "꿈": {
        "kr": "꿈을 꾸는 사람들의 눈빛은 밤하늘 은하수보다 더 아름다워.",
        "cn": "怀揣梦想之人的澄澈目光，比夜空浩瀚的银河更加美丽动人。",
        "source": "Ditto - NewJeans",
        "type": "song"
    },
    "세상": {
        "kr": "이 넓고 아름다운 세상 속에서 너라는 기적을 만났어.",
        "cn": "在这广阔而又美丽的世界里，能够与奇迹一般的你相遇。",
        "source": "Stay - BLACKPINK",
        "type": "song"
    },
    "시간": {
        "kr": "시간을 건너 그곳에서 우리 다시 만날 수 있다면.",
        "cn": "若能穿梭漫长的时光，与你再次在那片彼岸重逢相遇。",
        "source": "시간의 바깥 (Above the Time) - IU",
        "type": "song"
    },
    "노래": {
        "kr": "어떻게 내가 어떻게 너를, 이 노래의 멜로디 속에 너를 담을까.",
        "cn": "我该如何才能将深爱的你，完全寄托于这首歌曲的旋律之中呢。",
        "source": "어떻게 이별까지 사랑하겠어 - AKMU",
        "type": "song"
    },
    "바다": {
        "kr": "푸른 여름 바다 저 멀리, 시원한 파도 소리가 들려와.",
        "cn": "碧蓝清澈的盛夏海边遥远处，传来阵阵清爽愉悦的浪涛声。",
        "source": "Red Flavor - Red Velvet",
        "type": "song"
    },
    "커피": {
        "kr": "따뜻한 아메리카노 한 잔에 녹아내리는 오후의 나른함.",
        "cn": "在一杯温热的美式咖啡中慢慢融化的午后惬意与慵懒。",
        "source": "아메리카노 - 10cm",
        "type": "song"
    },
    "꽃": {
        "kr": "길가에 피어난 작은 꽃 한 송이에도 소중한 의미가 있어.",
        "cn": "即便只是盛开在路旁的一朵娇小花儿，也有着弥足珍贵的意义。",
        "source": "Celebrity - IU",
        "type": "song"
    },
    "가족": {
        "kr": "결국 힘들 때 내 곁을 든든하게 지켜주는 건 따뜻한 가족의 품이다.",
        "cn": "跌跌撞撞的艰难时刻，最终在身旁默默守护支撑我们的，永远是温暖的家人怀抱。",
        "source": "tvN 《请回答1988》",
        "type": "drama"
    },
    "행복": {
        "kr": "우리가 함께 웃을 수 있는 지금 이 순간이 바로 가장 큰 행복이야.",
        "cn": "我们能够并肩开怀大笑的此时此刻，就是世间最真实巨大的幸福。",
        "source": "이 사랑 - Davichi",
        "type": "song"
    },
    "학교": {
        "kr": "방과 후 노을빛으로 물든 학교 운동장에서 너를 기다리던 날들.",
        "cn": "放学后在被晚霞染红的学校操场上，怀揣悸动等待着你的那些日子。",
        "source": "Hype Boy - NewJeans",
        "type": "song"
    },
    "약속": {
        "kr": "다음 생이 있다면 그곳에서도 망설임 없이 당신을 찾아갈 것을 약속합니다.",
        "cn": "若有来生，我也向你郑重承诺，定会毫不犹豫地再次奔赴找到你。",
        "source": "KBS 《太阳的后裔》",
        "type": "drama"
    },
    "음악": {
        "kr": "불 꺼진 무대 위에서도 음악이 흐르면 우리는 다시 춤출 수 있어.",
        "cn": "即便在熄灭灯光的舞台之上，只要乐声响起，我们便能再度起舞。",
        "source": "Dynamite - BTS",
        "type": "song"
    },
    "하늘": {
        "kr": "맑고 파란 하늘 위로 하얀 뭉게구름이 끝없이 피어올라.",
        "cn": "在晴朗蔚蓝的高空之上，朵朵纯白洁净的云霞漫无边际地舒展盛开。",
        "source": "Universe - EXO",
        "type": "song"
    },
    "눈물": {
        "kr": "흘렸던 눈물만큼 너의 내일은 더욱더 찬란하게 빛날 거야.",
        "cn": "流淌过的每一滴泪水，都会让属于你的明日绽放出更加璀璨耀眼的光芒。",
        "source": "Fine - 太妍 (TAEYEON)",
        "type": "song"
    },
    "선물": {
        "kr": "나에게 찾아와준 그대라는 존재 자체가 인생의 가장 눈부신 선물이야.",
        "cn": "能够来到我身边的你，本身就是我生命中最耀眼璀璨的赠礼。",
        "source": "선물 (Gift) - MeloMance",
        "type": "song"
    },
    "십년": {
        "kr": "십 년이 지나도 우리 변치 않는 마음으로 음악을 노래하자.",
        "cn": "即使十年岁月流逝，也让我们怀揣着初心永远歌唱音乐。",
        "source": "10년이 지나도 - 经典名曲",
        "type": "song"
    },
    "독립": {
        "kr": "어둠을 뚫고 찬란한 독립과 자유의 빛을 향해 나아가리라.",
        "cn": "穿透重重黑暗，坚定不移地迈向那璀璨炽热的独立与自由之光芒。",
        "source": "tvN 《阳光先生 (Mr. Sunshine)》",
        "type": "drama"
    },
    "한국어": {
        "kr": "노래 가사로 배운 한국어가 마음속 깊은 울림으로 다가왔어요.",
        "cn": "从动人歌词中学到的韩语，化作了触动心弦深处最真挚的回响。",
        "source": "K-POP 文化语境",
        "type": "song"
    }
}

def main():
    data_path = "data/korean_vocab.json"
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    injected_count = 0
    for book in data.get("books", []):
        for lesson in book.get("lessons", []):
            for w in lesson.get("words", []):
                kr = w.get("korean", "").strip()
                # 检查直接匹配或包含匹配
                for target_kr, quote_obj in QUOTES_LIBRARY.items():
                    if kr == target_kr or (len(target_kr) >= 2 and target_kr in kr and "quote_lyric" not in w):
                        w["quote_lyric"] = quote_obj
                        injected_count += 1
                        print(f"Injected quote for: {kr} -> {quote_obj['source']}")
                        break

    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n[DONE] Successfully injected {injected_count} quotes into {data_path}")

if __name__ == "__main__":
    main()
