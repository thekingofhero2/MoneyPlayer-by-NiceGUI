def filter_think_tags( text: str) -> str:
        """过滤掉 <think> 标签内容，只保留正文"""
        # 查找最后一个 </think> 标签的位置
        end_think_index = text.rfind("</think>")
        if end_think_index != -1:
            # 返回 </think> 标签之后的内容
            text = text[end_think_index + len("</think>"):]
        return text