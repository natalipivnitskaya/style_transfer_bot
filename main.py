import os
import logging
import gc
import string
import random
from aiogram import Bot, Dispatcher, executor, types
from aiogram.utils.executor import start_webhook
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from decouple import config
from msg_net import *  # Import architecture
from utils import *  # Import functions
from transformer_net import *


os.environ['KMP_DUPLICATE_LIB_OK']='True'

# Set API_TOKEN
API_TOKEN = config('API_TOKEN')

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logging.debug('API_TOKEN={}'.format(API_TOKEN[:5]))

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())
models_root = './models/'

#Settings
# HASH = ''.join(random.choices(string.ascii_uppercase + string.ascii_lowercase + string.digits, k=16))
HASH = 'Q6XrSPxWvK1TSeqD'
HEROKU_APP_NAME = config('HEROKU_APP_NAME')
WEBHOOK_HOST = f'https://{HEROKU_APP_NAME}.herokuapp.com'
WEBHOOK_PATH = f'/webhook/{HASH}'
WEBHOOK_URL = f'{WEBHOOK_HOST}{WEBHOOK_PATH}'
WEBAPP_HOST = '0.0.0.0'
WEBAPP_PORT = int(config('PORT'))


# Initializing the flag to distinguish between images content and style.
flag = True
# Initializing flags to check for images.
content_flag = False
style_flag = False

device = ("cuda" if torch.cuda.is_available() else "cpu")

def transform(content_root, model, style_root = None):
    """Function for image transformation."""
    content_image = load_image(content_root, size = 225).to(device)
    content_image = Variable(content_image)
    if style_root: #Use of msg-net that generalized to all styles.
        style_model = MSGNet(ngf=128) #initialize the net
        style_model.load_state_dict(torch.load(models_root+model)) #upload weights
        style = load_image(style_root, size = 225).to(device)
        style_v = Variable(style)
        style_model.setTarget(style_v)
    else: #User wants build-in option style so use specifically style trained model.
        style_model = TransformerNet() #initialize the net
        style_model.load_state_dict(torch.load(models_root+model)) #upload weights
    
    output = style_model(content_image)
    save_image('result.jpg', output.data[0])

    # Clear the RAM.
    del style_model
    del content_image
    del output
    if style_root:
        del style
        del style_v
    torch.cuda.empty_cache()
    gc.collect()


@dp.message_handler(commands=['start'])
async def help_message(message: types.Message):
    """
    Outputs a small instruction when the corresponding command is received.
    """
    await message.answer(text="\n Hi there! "
                              "\n " 
                              "\nI am here to help you moving the style from one photo "
                              "to another."
                              "\n "   
                              "\nTo get started use /go command.")

@dp.message_handler(commands=['creator'])
async def creator(message: types.Message):
    """Displays information about the bot's Creator."""
    link = ''
    await message.answer(text="I have been created by Nataliya Pivnitskaya." 
                              "\nMy code is here: " + link)



@dp.message_handler(commands=['go'])
async def test(message: types.Message):
    """Test function"""
    await message.answer(text='Send me an image with the content, please.')



@dp.message_handler(content_types=['photo'])
async def photo_processing(message):
    """
    Triggered when the user sends an image and saves it for further processing.
    """

    global flag
    global content_flag
    global style_flag

    # The bot is waiting for a picture with content from the user.
    if flag:
        await message.photo[-1].download('content.jpg')
        await message.answer(text= 'I got the content image.')
        flag = False
        content_flag = True # Now the bot knows that the content image exists.

    # The bot is waiting for a picture with style from the user.
    else:
        await message.photo[-1].download('style.jpg')
        await message.answer(text= 'I got the style image.')
        style_flag = True  # Now the bot knows that the style image exists.

    res = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    res.add(types.KeyboardButton(text="Continue"))
    res.add(types.KeyboardButton(text="Reload"))
    await message.answer(text = 'Continue or Reload?', reply_markup=res)


@dp.message_handler(lambda message: message.text =='Reload')
async def photo_processing(message: types.Message):

    """Allows the user to select a different image with content or style."""

    global flag
    global content_flag
    global style_flag

    # Let's make sure that there is something to cancel.
    # if not content_flag:
    #     await message.answer(text="You haven't uploaded the content image yet.")
    #     return
    if not style_flag:
        await message.answer(text="Send me a new content image, please.")
        content_flag = False
        flag = True
    else:
        await message.answer(text="Send me a new style image, please.")
        style_flag = True
        #flag = False


@dp.message_handler(lambda message: message.text == 'Continue')
async def contin(message: types.Message):
    """Preparing for image processing."""

    logging.debug("Received message: Continue")
    global flag
    global content_flag
    global style_flag

    if not style_flag:
        res = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        res.add(types.KeyboardButton(text="Own style"))
        res.add(types.KeyboardButton(text="Build-in options"))

        await message.answer(text="Do you want to transfer you own style" 
                                  "\nor use build-in options?", reply_markup=res)

    else:
        await message.answer(text='Processing has started and will take about 10 secs. '
                                  '\n'
                                  '\nMeanwhile...'
                                  '\n- Why can’t dinosaurs clap?' 
                                  '\n- Because they are all dead.',
                             reply_markup=types.ReplyKeyboardRemove())
        transform('content.jpg', 'msgnet.pth', 'style.jpg')
        flag =  True
        content_flag =  False
        style_flag = False
        with open('result.jpg', 'rb') as file:
            await message.answer_photo(file, caption='Done!')


@dp.message_handler(lambda message: message.text in ("Own style", "Build-in options"))
async def processing(message: types.Message):
    """Uploading own style image."""
    
    global style_flag
    global flag
    
    if message.text == 'Own style':
        await message.answer(text='Upload your style image.')

    else:
        style_flag = True
        flag = True
        #Adding style options .
        res = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        res.add(types.KeyboardButton(text="Candy"))
        res.add(types.KeyboardButton(text="Mosaic"))
        res.add(types.KeyboardButton(text="Rain-Princess"))
        res.add(types.KeyboardButton(text="Udnie"))

        await message.answer(text="Choose the style option.", reply_markup=res)


@dp.message_handler(lambda message: message.text in ("Candy", "Mosaic", "Rain-Princess", "Udnie"))
async def processing(message: types.Message):
    """Image processing depending on the selected option."""

    global flag
    global content_flag
    global style_flag

    if message.text == "Candy":
        model = "candy.pth"
    if message.text == "Mosaic":
        model = "mosaic.pth"
    if message.text == "Rain-Princess":
        model = "rain_princess.pth"
    if message.text == "Udnie":
        model = "udnie.pth"

    await message.answer(text='Processing has started and will take about 10 secs. '
                              '\n'
                              '\nMeanwhile...'
                              '\n- Why can’t dinosaurs clap?' 
                              '\n- Because they are all dead.',
                         reply_markup=types.ReplyKeyboardRemove())

    transform('content.jpg', model)
    flag =  True
    content_flag =  False
    style_flag = False
    with open('result.jpg', 'rb') as file:
        await message.answer_photo(file, caption='Done!')

async def on_startup(dp):
    logging.warning('Registering webhook...')
    # await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)

async def on_shutdown(dp):
    logging.warning('Shutting down webhook connection')
    # await bot.delete_webhook()
    # Close DP connection (if used)
    await dp.storage.close()
    await dp.storage.wait_closed()
    logging.warning('Bye!')


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        skip_updates=True,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        host=WEBAPP_HOST,
        port=WEBAPP_PORT,
    )

    #executor.start_polling(dp, skip_updates=True)
