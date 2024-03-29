import discord
import CalendarSetup
import dateparser
import json
import random
import asyncio
import aiohttp
import requests

from discord.ext import commands
from dateutil.parser import parse as dtparse
from datetime import datetime
from datetime import timedelta
from dateutil.relativedelta import relativedelta

print('Starting bot...')

TOKEN = open('BotToken.txt', 'r').readline()
bot = commands.Bot(command_prefix='!')


@bot.command()
async def ping(ctx):
    await ctx.send(f'Pong! {round (bot.latency * 1000)}ms')


@bot.command()
async def link(ctx):
    await ctx.send('Linking account')
    service = CalendarSetup.get_calendar_service()
    await ctx.send('Account linked')
    calendar_id = get_calendar_id(service)
    if(calendar_id == None):
        with open('setting.json') as f:
            timezone = json.load(f)['timezone']
        calendar = {
            'summary': 'Due Dates',
            'timeZone': timezone
        }
        created_calendar = service.calendars().insert(body=calendar).execute()
        calendarId = created_calendar['id']
        await ctx.send('Due Dates calendar created')
    else:
        await ctx.send('Due Dates calendar found')


@bot.command()
async def day(ctx):
    service = CalendarSetup.get_calendar_service()
    calendar_id = get_calendar_id(service)
    now = datetime.now()
    start_of_day = datetime(now.year, now.month, now.day)
    end_of_day = start_of_day + timedelta(days=1)
    active = get_events_by_date(service, calendar_id, start_of_day, end_of_day)
    active.sort()

    embed = discord.Embed(title='Due today', colour=discord.Colour.red())
    for event in active:
        embed.add_field(name=event[1], value=event[0].strftime(
            '%I:%M %p'), inline=False)

    await ctx.send(embed=embed)


@bot.command()
async def week(ctx):
    service = CalendarSetup.get_calendar_service()
    calendar_id = get_calendar_id(service)
    now = datetime.now()
    start_of_day = datetime(now.year, now.month, now.day)
    end_of_day = start_of_day + timedelta(weeks=1)
    active = get_events_by_date(service, calendar_id, start_of_day, end_of_day)
    active.sort()

    embed = discord.Embed(title='Due this week', colour=discord.Colour.red())
    for event in active:
        embed.add_field(name=event[1], value=event[0].strftime(
            '%d-%b %a %I:%M %p'), inline=False)

    await ctx.send(embed=embed)


@bot.command()
async def month(ctx):
    service = CalendarSetup.get_calendar_service()
    calendar_id = get_calendar_id(service)
    now = datetime.now()
    start_of_day = datetime(now.year, now.month, now.day)
    end_of_day = start_of_day + relativedelta(months=+1)
    active = get_events_by_date(service, calendar_id, start_of_day, end_of_day)
    active.sort()

    embed = discord.Embed(title='Due this month', colour=discord.Colour.red())
    for event in active:
        embed.add_field(name=event[1], value=event[0].strftime(
            '%d-%b %a %I:%M %p'), inline=False)

    await ctx.send(embed=embed)

@bot.command()
async def create(ctx, *, msg):
    service = CalendarSetup.get_calendar_service()
    calendar_id = get_calendar_id(service)
    calendar = service.calendars().get(calendarId=calendar_id).execute()
    with open('setting.json') as f:
        timezone = json.load(f)['timezone']

    info = msg.split(',', 1)
    title = info[0]
    original_date = dateparser.parse(info[1])
    date = original_date.isoformat('T')

    event = {
        'summary': title,
        'start': {
            'dateTime': date,
            'timeZone': timezone,
        },
        'end': {
            'dateTime': date,
            'timeZone': timezone,
        },
    }

    event = service.events().insert(calendarId=calendar_id, body=event).execute()
    await ctx.send('{} created at {}'.format(title, original_date))


@bot.command()
async def delete(ctx, *, msg):
    service = CalendarSetup.get_calendar_service()
    calendar_id = get_calendar_id(service)
    event_id = get_event_id(service, calendar_id, msg)
    if(event_id != None):
        service.events().delete(calendarId=calendar_id,
                                eventId=event_id).execute()
        await ctx.send('Deleted ' + msg)
    else:
        await ctx.send(msg + ' not found')


@bot.command()
async def update(ctx, *, msg):
    service = CalendarSetup.get_calendar_service()
    calendar_id = get_calendar_id(service)
    info = msg.split(',', 1)
    title = info[0]
    event_id = get_event_id(service, calendar_id, title)
    original_date = dateparser.parse(info[1])
    date = original_date.isoformat('T')

    if(event_id != None):
        event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        event['start']['dateTime'] = date
        event['end']['dateTime'] = date
        updated_event = service.events().update(
            calendarId=calendar_id, eventId=event_id, body=event).execute()
        original_date = original_date.strftime('%d-%b-%y %a %I:%M %p')
        await ctx.send('Updated {} to {}'.format(title, original_date))
    else:
        await ctx.send('{} not found'.format(title))


@bot.event
async def on_command_error(ctx, error):
    await ctx.send(f'{error}\n\nTry !help')

# We delete default help command
bot.remove_command('help')


# Embeded help with list and details of commands
@bot.command(pass_context=True)
async def help(ctx):
    embed = discord.Embed(colour=discord.Colour.green())
    embed.set_author(name='Help : list of commands available')
    embed.add_field(
        name='!link', value='''Authorize the bot to access your google calendar.
                            All event created will be on a calendar called "Due Dates"''', inline=False)
    embed.add_field(
        name='!ping', value='Returns bot response time in milliseconds', inline=False)
    embed.add_field(
        name='!create', value='''Creates an event in Google Calendar.
                            Ex) !create eventname, YYYY MMM 3 10:00pm, ''', inline=False)
    embed.add_field(
        name='!delete', value='''Deletes an event in Google Calendar.
                            Ex) !delete id''', inline=False)
    embed.add_field(
        name='!update', value='''Updates an event to a different time/date.
                            Ex)!update id ''', inline=False)
    embed.add_field(
        name='!day', value='''Returns all events today.
                            Ex)!day ''', inline=False)
    embed.add_field(
        name='!week', value='''Return all events this week.
                            Ex)!week ''', inline=False)
    embed.add_field(
        name='!month', value='''Return all events this month.
                            Ex)!month ''', inline=False)

    await ctx.send(embed=embed)


def get_calendar_id(service):
    page_token = None
    cal_not_found = True
    while cal_not_found:
        calendar_list = service.calendarList().list(pageToken=page_token).execute()
        for calendar_list_entry in calendar_list['items']:
            if(calendar_list_entry['summary'] == 'Due Dates'):
                return calendar_list_entry['id']
        page_token = calendar_list.get('nextPageToken')
        if not page_token:
            break
    return None


def get_event_id(service, calendar_id, name):
    page_token = None
    while True:
        events = service.events().list(calendarId=calendar_id,
                                       pageToken=page_token).execute()
        for event in events['items']:
            if(event['summary'] == name):
                return event['id']

        page_token = events.get('nextPageToken')
        if not page_token:
            break
    return None


def get_events_by_date(service, calendar_id, start_date, end_date):
    page_token = None
    found = []
    while True:
        events = service.events().list(calendarId=calendar_id,
                                       pageToken=page_token).execute()
        for event in events['items']:
            due_date = dtparse(event['start']['dateTime']).replace(tzinfo=None)
            if(start_date < due_date < end_date):
                found.append((due_date, event['summary']))
        page_token = events.get('nextPageToken')
        if not page_token:
            break

    return found


@bot.command()
async def launch(ctx):
    await ctx.send('Nuclear Bomb Has Launched!')
    await ctx.send('https://imgur.com/vz7Fu1m')
    await ctx.send('https://imgur.com/VyCuDYd')


@bot.command(aliases=['askme','test1'])
async def _askme(ctx, *, q):
    respond = ["It is certain.",
                "It is decidedly so.",
                "Without a doubt.",
                "Yes - definitely.",
                "You may rely on it.",
                "As I see it, yes.",
                "Most likely.",
                "Outlook good.",
                "Yes.",
                "Signs point to yes.",
                "Reply hazy, try again.",
                "Ask again later.",
                "Better not tell you now.",
                "Cannot predict now.",
                "Concentrate and ask again.",
                "Don't count on it.",
                "My reply is no.",
                "My sources say no.",
                "Outlook not so good.",
                "Very doubtful."
                ]
    await ctx.send(f'Question:{q}\nAnswer: {random.choice(respond)}')

@bot.command()
async def bitcoin(ctx):
    url = 'https://api.coindesk.com/v1/bpi/currentprice/BTC.json'
    async with aiohttp.ClientSession() as session:  # Async HTTP request
        raw_response = await session.get(url)
        response = await raw_response.text()
        response = json.loads(response)
        await ctx.send("Bitcoin price is: $" + response['bpi']['USD']['rate'])


@bot.command()
async def msgday(ctx):
    responds = ["You’re off to great places, today is your day. Your mountain is waiting, so get on your way.",
                "You always pass failure on the way to success.",
                "No one is perfect - that’s why pencils have erasers.",
                "Winning doesn’t always mean being first. Winning means you’re doing better than you’vedone before.",
                "You’re braver than you believe, and stronger than you seem, and smarter than you think.",
                "It always seems impossible until it is done.",
                "Keep your face to the sunshine and you cannot see a shadow.",
                "Once you replace negative thoughts with positive ones, you’ll start having positive results.",
                "Positive thinking will let you do everything better than negative thinking will.",
                "In every day, there are 1,440 minutes. That means we have 1,440 daily opportunities to make a positive impact.",
                "The only time you fail is when you fall down and stay down.",
                "Virtually nothing is impossible in this world if you just put your mind to it and maintain a positive attitude.",
                "Optimism is a happiness magnet. If you stay positive good things and good people will be drawn to you.",
                "It makes a big difference in your life when you stay positive."
                ]
    await ctx.send(f'Message of the day\n" {random.choice(responds)}"')


print("Bot is ready!")
bot.run(TOKEN)
