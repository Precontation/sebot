import discord
import dotenv
import os
import asyncio
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

dotenv.load_dotenv()

# Discord stuff
intents = discord.Intents.default()
intents.message_content = True

discord_client = discord.Client(
    intents=intents,
    allowed_mentions=discord.AllowedMentions(
        users=True, roles=False, everyone=False, replied_user=True
    ),
)
tree = discord.app_commands.CommandTree(discord_client)

# Modal AI stuff
MODAL_BEARER_TOKEN = os.environ["MODAL_BEARER_TOKEN"]
MODAL_URL = os.environ["MODAL_URL"]

modal_client = AsyncOpenAI(
    base_url=f"{MODAL_URL}/v1",
    api_key=MODAL_BEARER_TOKEN,
)

# System prompt
system_prompt = "You're name is Sebot. Don't send gifs or image URLs."
custom_system_prompt = ""
remove_original_system_prompt = False

# Consts
ERROR_MESSAGE = "An error occurred :("
ASSISTANT_MESSAGE_PREFIX = "Sebot: "
OWNER_USER_ID = 766046835109789716
MAX_CONTEXT_MESSAGES = 5
AI_MODEL = "Precontation/sebot-hf"


async def get_ai_message(formatted_messages: list[ChatCompletionMessageParam]):
    try:
        prompt = f"{system_prompt}\nWhen referring to users, use their name without an @ symbol. User messages may be formatted as Username: message. The text before the first colon is the speaker's username and is not part of what they said."

        if remove_original_system_prompt:
            prompt = custom_system_prompt
        elif custom_system_prompt != "":
            prompt += (
                "\n\nIn addition to the system prompt, a custom one was added: "
                + custom_system_prompt
            )

        formatted_prompt: ChatCompletionMessageParam = {
            "role": "system",
            "content": prompt,
        }

        messages: list[ChatCompletionMessageParam] = [
            formatted_prompt
        ] + formatted_messages

        completion = await asyncio.wait_for(
            modal_client.chat.completions.create(
                model=AI_MODEL,
                messages=messages,
                temperature=0.6,
                max_completion_tokens=500,
                top_p=1,
                stream=False,
                extra_body={"chat_template_kwargs": {"enable_thinking": False}},
            ),
            timeout=60,
        )
    except Exception as e:
        print(f"Modal failed! Error: {e}")
        return ERROR_MESSAGE

    if len(completion.choices) != 0 and completion.choices[0].message.content:
        return completion.choices[0].message.content
    else:
        return ERROR_MESSAGE


@discord_client.event
async def on_ready():
    await tree.sync()
    print(f"Bot is logged in and ready!")


@discord_client.event
async def on_message(message: discord.Message):
    if not (
        (discord_client.user in message.mentions or message.guild is None)
        and message.author != discord_client.user
    ):
        return

    async with message.channel.typing():
        messages: list[discord.Message] = []
        messages = [
            m async for m in message.channel.history(limit=MAX_CONTEXT_MESSAGES)
        ]
        messages.reverse()  # Reverse it to make it chronological now

        formattedMessages: list[ChatCompletionMessageParam] = []

        for m in messages:
            content = m.author.display_name + ": " + m.clean_content
            if m.author == discord_client.user:
                if m.clean_content == ERROR_MESSAGE:
                    continue  # Don't have it knowing it errored!

                formattedMessages.append(
                    {
                        "role": "assistant",
                        "content": content.removeprefix(
                            ASSISTANT_MESSAGE_PREFIX
                        ),  # Remove so the AI doesn't bug out and go insane
                    }
                )
            else:
                formattedMessages.append({"role": "user", "content": content})

        message_response = await get_ai_message(formattedMessages)
        await message.reply(message_response)


@tree.command(name="ask", description="Ask Sebot a question")
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@discord.app_commands.allowed_installs(guilds=True, users=True)
async def ask(interaction: discord.Interaction, question: str):
    await interaction.response.defer()

    message_response = await get_ai_message([{"role": "user", "content": question}])

    await interaction.followup.send(
        f"{interaction.user.display_name}: {question}\n{ASSISTANT_MESSAGE_PREFIX}{message_response}"
    )


@tree.command(
    name="set_prompt", description="YOU DONT GET TO USE ONLY I DO ASKDLFJALSDKJF"
)
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@discord.app_commands.allowed_installs(guilds=True, users=True)
async def set_prompt(
    interaction: discord.Interaction, prompt: str = "", replace_original: bool = False
):
    global custom_system_prompt
    global remove_original_system_prompt

    if interaction.user.id != OWNER_USER_ID:
        await interaction.response.send_message(
            f"nuh uh you no dont use", ephemeral=True
        )
        return

    custom_system_prompt = prompt
    remove_original_system_prompt = replace_original

    await interaction.response.send_message(
        f"k set 🫪🫪🫪🫪🫪🫪🫪🫪🫪🫪🫪🫪🫪🫪🫪🫪🫪🫪🫪🫪🫪🫪🫪🫪🫪🫪🫪",
        ephemeral=True,
    )


discord_client.run(os.environ["DISCORD_BOT_TOKEN"])
