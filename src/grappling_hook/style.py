# written by claude cuz i dont want to have to deal with this bs

from inquirer.render.console import ConsoleRender
from inquirer.themes import Theme, term


class Label(Theme):
    def __init__(self):
        super().__init__()
        self.Question.mark_color = term.white
        self.Question.brackets_color = term.white
        self.Question.default_color = term.white
        self.List.selection_color = term.white
        self.List.selection_cursor = ">"
        self.List.unselected_color = term.white
        self.Checkbox.selection_color = term.white
        self.Checkbox.selection_icon = ">"
        self.Checkbox.selected_color = term.white
        self.Checkbox.selected_icon = "[x]"
        self.Checkbox.unselected_color = term.white
        self.Checkbox.unselected_icon = "[ ]"


class Render(ConsoleRender):
    def _print_header(self, render):
        base = render.get_header()
        header = base[: self.width - 9] + "..." if len(base) > self.width - 6 else base
        default_value = " ({color}{default}{normal})".format(
            default=render.question.default, color=self._theme.Question.default_color, normal=self.terminal.normal
        )
        show_default = render.question.default and render.show_default
        header += default_value if show_default else ""
        msg_template = "{t.move_up}{t.clear_eol}{msg}"

        escaped_current_value = str(render.get_current_value()).replace("{", "{{").replace("}", "}}")
        self.print_str(
            f"\n{msg_template} {escaped_current_value}",
            msg=header,
            lf=not render.title_inline,
            tq=self._theme.Question,
        )

    def _print_options(self, render):
        for message, symbol, color in render.get_options():
            if hasattr(message, "decode"):  # python 2
                message = message.decode("utf-8")
            self.print_line("{color}{s} {m}{t.normal}", m=message, color=color, s=symbol)

    def render(self, question, answers=None):
        question.answers = answers or {}
        if question.ignore:
            return question.default

        clazz = self.render_factory(question.kind)
        render = clazz(question, terminal=self.terminal, theme=self._theme, show_default=question.show_default)

        self.clear_eos()
        result = self._event_loop(render)

        if question.kind == "list":
            answer = str(render.question.choices[render.current])
        elif question.kind == "checkbox":
            answer = ", ".join(str(render.question.choices[i]) for i in render.selection)
        else:
            answer = None

        if answer is not None:
            rows = len(list(render.get_options())) + 1
            print(self.terminal.move_up * rows + self.terminal.clear_eos(), end="")
            print(f"{question.message} {answer}")

        return result


def render() -> ConsoleRender:
    return Render(theme=Label())
