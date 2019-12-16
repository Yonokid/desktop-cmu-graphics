#!/usr/bin/env python

import argparse
import os
import sys
import time
import traceback

import imageio
from PIL import Image
import numpy

import subprocess
from shutil import copy2

SIZE = 400

REPORT_FILE = None

TEST_FILE_PATH = './runner.py'

REPORT_HEADER = '''
<html>
<head>
<style>
div.error {
    padding-bottom: 10px;
    margin-bottom: 60px;
    background: #eee;
}
div.error img {
    margin-right: 10px;
    border: 1px solid black;
}
</style>
</head>
<body>
'''
REPORT_FOOTER = '</body></html>'

IS_CI = os.environ.get('CI', 'false') == 'true'
if IS_CI:
    S3 = boto3.resource('s3')
    S3_BUCKET = S3.Bucket('cmu-cs-academy.backend.files.eddie')

def compare_images(path_1, path_2, test_name, test_piece_i, threshold=25):
    image_1 = Image.open(path_1)
    image_1 = image_1.convert("RGB")
    image_1.save(path_1)
    image_1_data = imageio.imread(path_1)

    image_2 = Image.open(path_2)
    image_2 = image_2.convert("RGB")
    image_2.save(path_2)
    image_2_data = imageio.imread(path_2)

    assert image_1_data.shape == (SIZE, SIZE, 3)
    assert image_2_data.shape == (SIZE, SIZE, 3)
    assert image_1_data.shape == image_2_data.shape, image_2_data.shape

    error_array = (image_1_data.astype('float') - image_2_data.astype('float')) ** 2
    mean_squared_error = numpy.sum(error_array) / float(SIZE * SIZE)

    if mean_squared_error >= threshold:
        diff_image_path = 'image_gen/%s/diff_%d.png' % (test_name, test_piece_i)

        per_pixel_error = error_array.sum(axis=2)

        visual_diff = numpy.zeros((SIZE, SIZE, 4), dtype=numpy.uint8)
        for i in range(SIZE):
            for j in range(SIZE):
                this_error = per_pixel_error[i][j]
                if this_error > 0:
                    if this_error < threshold:
                        visual_diff[i][j][2] = 255  # blue
                    else:
                        visual_diff[i][j][0] = 255  # red
                    visual_diff[i][j][3] = 128  # half alpha

        imageio.imwrite(diff_image_path, visual_diff)
        # if IS_CI:
        #     S3_BUCKET.put_object(
        #         Key='test_image_gen/%s' % path_2.replace('/', '_'),
        #         Body=open(path_2, 'rb'))
        #     S3_BUCKET.put_object(
        #         Key='test_image_gen/%s' % diff_image_path.replace('/', '_'),
        #         Body=open(diff_image_path, 'rb'))
        # print("Part %d MSE %.0f" % (test_piece_i, mean_squared_error))
        REPORT_FILE.write("<div class='error'><p>Part %d MSE %.0f</p>" %
            (test_piece_i, mean_squared_error))
        for path in [path_1, path_2, diff_image_path]:
            REPORT_FILE.write("<img src='%s' />" % path)

    return mean_squared_error < threshold

def run_test(driver, test_name, all_source_code):
    source_code_pieces = all_source_code.split('\n# -\n')
    source_code = ''
    i = 0
    all_passed = True

    addEventFnCaller = {
        'onKeyHolds': '\ndef onKeyHolds(keys, n):\n    for i in range(n):\n        onKeyHold(keys)\n',
        'onSteps': '\ndef onSteps(n):\n    for i in range(n):\n        onStep()\n',
        'onKeyPresses': '\ndef onKeyPresses(key, n):\n    for i in range(n):\n        onKeyPress(key)\n',
        'onMousePresses': '\ndef onMousePresses(mouseX, mouseY, n):\n    for i in range(n):\n        onMousePress(mouseX, mouseY)\n'
    }

    for piece_i in range(len(source_code_pieces)):
        # skip exercises with random calls
        if 'randrange' in source_code_pieces[piece_i] or 'onMouseMove' in source_code_pieces[piece_i]:
            continue

        i += 1

        if not os.path.exists('image_gen/%s' % test_name):
            os.mkdir('image_gen/%s' % test_name)

        correct_path = 'image_gen/%s/correct_%d.png' % (test_name, i)
        output_path = 'image_gen/%s/output_%d.png' % (test_name, i)

        if not os.path.exists(output_path):
            print('Generating new %s' % output_path)
            copy2('cs-academy-canvas.png', output_path)

        source_code = r''
        source_code += 'import sys'
        source_code += '\nsys.path.insert(0, "..")'
        source_code += '\nfrom cmu_graphics import *\n'
        # source_code += '\n######\n'.join(source_code_pieces[:piece_i])
        # source_code += '\ndef onMousePress(x, y):\n'
        source_code += '\n'.join([(s) for s in source_code_pieces[piece_i].split('\n')])

        # if any event wrapper is called, insert a definition for it above the first line.
        for val in addEventFnCaller.keys():
            ind = 0
            source_code_lines = source_code.split('\n')
            for line in source_code_lines:
                if (line.find(val) != -1):
                    break
                ind += 1

            if ind != len(source_code.split('\n')):
                addedStr = addEventFnCaller[val]
                source_code_lines.insert(ind-1, addedStr)
                source_code = '\n\n'.join(list(source_code_lines))

        source_code += '\napp.background = "honeydew"'
        source_code += '\napp.paused = True'
        source_code += '\nfrom threading import Timer\n'
        source_code += '\nimport time\n'
        source_code += 'def screenshotAndExit():\n'
        # source_code += '    app.callUserFn("onMousePress", (200,200))\n'
        source_code += '    time.sleep(1)\n'
        source_code += '    app.getScreenshot("%s")\n' % os.path.abspath(output_path).replace('\\', '/')
        source_code += '    app.quit()\n'
        source_code += 'Timer(3, screenshotAndExit).start()\n'
        source_code += 'cmu_graphics.loop()'

        # print(source_code)
        # print('###################################################################')

        with open(TEST_FILE_PATH, 'w') as f:
            f.write(source_code)

        p = subprocess.Popen(
            [sys.executable, TEST_FILE_PATH],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = p.communicate()
        console_output = stdout + stderr

        if stderr != b'':
            print(stdout.decode('utf-8'))
            print(stderr.decode('utf-8'))
            os._exit(0)

        if not os.path.exists(correct_path):
            print('Generating new %s' % correct_path)
            os.system('cp %s %s' % (output_path, correct_path))
            continue
        else:
            if not compare_images(correct_path, output_path, test_name, i,
                    threshold=50 if 'Label' in source_code else 25):
                if console_output.strip():
                    REPORT_FILE.write(
                        '<p>Console output for part %d:</p><pre>%s</pre>' %
                        (i, console_output))
                REPORT_FILE.write(
                    '<p>Source code for part %d:</p><pre>%s</pre>' % (i, source_code))
                all_passed = False

    return all_passed

def main():
    global REPORT_FILE, WAIT

    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=str, default='../CMU_CS_Academy_CS_1/', nargs='?')
    parser.add_argument('--only', type=str, help='The name of a single python file to run')

    args = parser.parse_args()

    num_failures = 0
    num_successes = 0
    start_time = time.time()
    driver = None

    try:
        REPORT_FILE = open('report.html', 'w')
        REPORT_FILE.write(REPORT_HEADER)

        for test_py_name in (args.only and [args.only] or os.listdir('image_gen')):
            if not test_py_name.endswith('.py'):
                continue
            REPORT_FILE.flush()
            with open('image_gen/%s' % test_py_name) as f:
                if not run_test(driver, test_py_name[:-3], f.read()):
                    print('image_gen/%s failed' % test_py_name)
                    REPORT_FILE.write('<p>image_gen/%s failed' % (test_py_name))
                    REPORT_FILE.write('</div>')
                    num_failures += 1
                else:
                    num_successes += 1

        if num_failures > 0:
            sys.exit(1)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            REPORT_FILE.write(REPORT_FOOTER)
            REPORT_FILE.close()
        except:
            pass
        try:
            if driver:
                print('Saving screenshot in final_screenshot.png')
                driver.save_screenshot('final_screenshot.png')
                if IS_CI:
                    print('Saving screenshot in s3://cmu-cs-academy.backend.files.eddie/test_image_gen/final.png')
                    S3.Bucket('cmu-cs-academy.backend.files.eddie').put_object(
                        Key='test_image_gen/final.png', Body=open('final_screenshot.png', 'rb'))
        except:
            print('Exception saving screenshot')
            traceback.print_exc()
        try:
            driver.close()
        except:
            pass
        # try:
        #     os.remove(TEST_FILE_PATH)
        # except:
        #     pass
        print('\n\n%d successes and %d failures in %.1fs' % (
            num_successes, num_failures, time.time() - start_time))
        print('See report.html for details')

if __name__ == '__main__':
    main()
