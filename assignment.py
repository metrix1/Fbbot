import smtplib
import requests
from email.message import EmailMessage
from email.utils import formatdate
from pprint import pprint
import os
import discord
from discord.ext import commands
import discord.ext
from dotenv import load_dotenv
from typing import List, Dict
import random


load_dotenv()

SMTP_SERVER = os.environ.get("SMTP_SERVER")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD")
TOKEN = os.getenv("DISCORD_TOKEN")
IMGFLIP_USERNAME = os.environ.get("IMGFLIP_USERNAME")
IMGFLIP_PASSWORD = os.environ.get("IMGFLIP_PASSWORD")
CAPTION_IMAGE_URL = "https://api.imgflip.com/caption_image"
GET_MEMES_URL = "https://api.imgflip.com/get_memes"


intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", case_insensitive=True, intents=intents)

# --------- EMAIL SENDER ----------


class SMTP_SSL_wrapper:
    def __init__(self, server: str, username: str, password: str):
        self.server = server
        self.port = 465
        self.username = username
        self.password = password

    def send_email(self, recipient: str,
                   subject: str, content: str) -> EmailMessage:
        email_msg = EmailMessage()
        email_msg.set_content(content)
        email_msg["From"] = self.username
        email_msg["To"] = recipient
        email_msg["Date"] = formatdate(localtime=True)
        email_msg["Subject"] = subject

        s = smtplib.SMTP_SSL(self.server, port=self.port)
        s.login(self.username, self.password)
        errors = s.send_message(email_msg)
        s.quit()

        if len(errors):
            print("Errors occured during sending:")
            pprint(errors)
        else:
            print("OK - message submitted for delivery.")
            print("Later on some errors might occur, but we won't know.")


if __name__ == "__main__":
    smtp_interface = SMTP_SSL_wrapper(
        server=SMTP_SERVER, username=SENDER_EMAIL, password=SENDER_PASSWORD
    )


class MemeGenerator:
    def list_memes(self) -> str:
        string_of_memes: str = ""
        response = requests.get(GET_MEMES_URL).json()

        for i in range(25):
            string_of_memes += (
                response["data"]["memes"][i]["id"]
                + " "
                + response["data"]["memes"][i]["name"]
                + "\n"
            )
        return string_of_memes

    def make_meme(self, template_id: int,
                  top_text: str, bottom_text: str) -> str:
        params = {
            "template_id": template_id,
            "username": IMGFLIP_USERNAME,
            "password": IMGFLIP_PASSWORD,
            "text0": top_text,
            "text1": bottom_text,
        }

        response_from_poste = requests.post(CAPTION_IMAGE_URL, params).json()
        return response_from_poste["data"]["url"]


class MentionsNotifier:
    _emails = List[str]
    _ids = List[int]

    def subscribe(self, id: int, email: str) -> bool:
        if id not in self._ids:
            self._emails.append(email)
            self._ids.append(id)
            already_in = False
        else:
            self._emails[self._ids.index(id)] = email
            already_in = True

        return already_in

    def unsubscribe(self, id: int) -> bool:
        if id not in self._ids:
            already_in = False
        else:
            index_id = self._ids.index(id)

            self._emails.remove(self._emails[index_id])
            self._ids.remove(id)
            already_in = True

        return already_in

    def GetEmail(self, id: int):
        try:
            return self._emails[self._ids.index(id)], True
        except (ValueError):
            return "", False


class Hangman:
    people_playing_list = {}

    async def play_hangman(self, ctx, hangman_player) -> None:
        await ctx.send("**Hangman**")
        await ctx.send("Player: " + hangman_player.name)
        hangman_player.guess_message = await ctx.send("Guess: ")
        hangman_player.lives_message = await ctx.send("Lives: 7")
        hangman_player.word_message = await ctx.send(
            "Word: " + str(" ".join(hangman_player.dashed_word))
        )
        hangman_player.ending_message = await ctx.send("Good luck!")

    async def guess_letter(self, ctx, hangman_player, letter) -> str:
        if letter in hangman_player.guesses:
            hangman_player.ending_phrase = "You already guessed that."

        else:
            if letter in hangman_player.word:
                await self.reveal_some_letters(hangman_player, letter)
                hangman_player.guesses.append(letter)

                if await self.is_every_letter_in_word(hangman_player):
                    hangman_player.ending_phrase = "You won!"
                    Hangman.people_playing_list.pop(ctx.author.id)
                    return

                hangman_player.ending_phrase = "Correct guess."
            else:
                hangman_player.lives -= 1
                hangman_player.guesses.append(letter)

                if hangman_player.lives == 0:
                    Hangman.people_playing_list.pop(ctx.author.id)
                    hangman_player.ending_phrase = (
                        "You lost! The word was: " + hangman_player.word
                    )
                    return

                hangman_player.ending_phrase = "Wrong guess."

    async def refresh_messages(self, hangman_player):
        joined_guesses = str(", ".join(hangman_player.guesses))
        joined_dashed_word = str(" ".join(hangman_player.dashed_word))
        await hangman_player.guess_message.edit(
            content=("Guess: " + joined_guesses)
        )
        await hangman_player.lives_message.edit(
            content=("Lives: " + str(hangman_player.lives))
        )
        await hangman_player.word_message.edit(
            content=("Word: " + joined_dashed_word)
        )
        await hangman_player.ending_message.edit(
            content=(hangman_player.ending_phrase)
        )

    async def return_specific_hangman_player(self, id) -> object:
        return Hangman.people_playing_list.get(id)

    async def is_he_playing(self, id) -> bool:
        if id in Hangman.people_playing_list:
            return True
        else:
            return False

    async def is_every_letter_in_word(self, hangman_player) -> bool:
        """"
        Checking if player guessed all right letters

        Returning True if the condition is met
        """
        copy_of_dashed_word = hangman_player.dashed_word.copy()

        for letter in hangman_player.word:
            try:
                copy_of_dashed_word.remove(letter)
            except (ValueError):
                pass

        if not len(copy_of_dashed_word):
            return True
        else:
            return False

    async def reveal_some_letters(self, hangman_player, letter) -> None:
        """Replaces dashes with right guessed letter"""

        list_indexes_of_letter = [
            i for i, ltr in enumerate(hangman_player.word) if ltr == letter
        ]

        for j in list_indexes_of_letter:
            hangman_player.dashed_word[j] = letter


class HangmanPlayer:
    def __init__(self, id: int, name: str):
        self.id = id
        self.name = name
        self.guesses: List[chr] = []
        self.lives = 7
        self.word = self.random_line_from_words()[:-1].upper()
        self.dashed_word = self.dashes_instead_letters(self.word)

        self.guess_message = None
        self.lives_message = None
        self.word_message = None
        self.ending_message = None
        self.ending_phrase = None

    def random_line_from_words(self) -> str:
        return random.choice(list(open("words.txt")))

    def dashes_instead_letters(self, word) -> List[chr]:
        """
        Returning list of dashes.

        Returns a list of dashes with the same length as the parameter.
        """
        list_of_dashes: List[str] = []
        for _ in word:
            list_of_dashes.append("-")

        return list_of_dashes


# --------- LEVEL 1 ----------
meme_generator = MemeGenerator()


@bot.command(name="list_memes")
async def list_memes(ctx: commands.Context) -> None:
    meme_list = meme_generator.list_memes()
    await ctx.send(meme_list)


@bot.command(name="make_meme")
async def make_meme(
    ctx: commands.Context, template_id: int, top_text: str, bottom_text: str
) -> None:
    meme_url = meme_generator.make_meme(template_id, top_text, bottom_text)
    await ctx.send(meme_url)


# --------- LEVEL 2 ----------
mentions_notifier = MentionsNotifier()


@bot.command(name="subscribe")
async def subscribe(ctx: commands.Context, email: str) -> None:

    already_in = mentions_notifier.subscribe(ctx.author.id, email)
    if already_in:
        await ctx.send("Already in subscriber list, your email was changed!")
    else:
        await ctx.send("You were added to subscriber list!")


@bot.command(name="unsubscribe")
async def unsubscribe(ctx: commands.Context) -> None:

    already_in = mentions_notifier.subscribe(ctx.author.id)
    if already_in:
        await ctx.send("You were removed from subscriber list!")
    else:
        await ctx.send("You are not in subscriber list, nothing changed")


@bot.event
async def on_message(message: discord.Message) -> None:

    await bot.process_commands(message)
    if not message.author == bot.user:
        for menti in message.mentions:
            potencialemail, passed = mentions_notifier.GetEmail(menti.id)
            if passed:
                email = potencialemail
                subject = "New mention just arrived"
                content = (
                  "Someone mentioned you in channel " + str(message.jump_url))
                print("program send email, wait for possible errors")
                smtp_interface.send_email(email, subject, content)


# --------- LEVEL 3 ----------
hangman = Hangman()


@bot.command(name="play_hangman")
async def play_hangman(ctx: commands.Context) -> None:

    if not await hangman.is_he_playing(ctx.author.id):

        hangman_player = HangmanPlayer(ctx.author.id, ctx.author.name)
        Hangman.people_playing_list[ctx.author.id] = hangman_player

        await hangman.play_hangman(ctx, hangman_player)

    else:
        await ctx.send("You are already playing!")


@bot.command(name="guess")
async def guess(ctx: commands.Context, letter: str) -> None:

    if await hangman.is_he_playing(ctx.author.id):

        hangman_player = (
            await hangman.return_specific_hangman_player(ctx.author.id))

        await hangman.guess_letter(ctx, hangman_player, letter.upper())
        await hangman.refresh_messages(hangman_player)

    else:
        await ctx.send("you have to create a new game first - !play_hangman")

    await ctx.message.delete()


bot.run(TOKEN)
