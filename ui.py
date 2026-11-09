import discord


class OwnerView(discord.ui.View):
    """Зөвхөн командыг дуудсан хүн ашиглаж чадах цэс."""

    def __init__(self, owner_id: int, timeout: float = 120):
        super().__init__(timeout=timeout)
        self.owner_id = owner_id
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "❌ Энэ цэс таных биш. Өөрөө команд ажиллуулна уу.", ephemeral=True
            )
            return False
        return True

    def disable_all(self):
        for child in self.children:
            child.disabled = True

    async def on_timeout(self):
        self.disable_all()
        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except Exception:
                pass


def nav_button(label: str, callback, style=None, disabled: bool = False):
    btn = discord.ui.Button(
        label=label,
        style=style or discord.ButtonStyle.secondary,
        disabled=disabled,
    )
    btn.callback = callback
    return btn
