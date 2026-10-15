// Run against a disposable test server only; requires Playwright and Chromium.
const assert=require('node:assert/strict');
const {chromium}=require('playwright');
(async()=>{
 const alt=process.env.CHROMIUM_MODULE?(await import(process.env.CHROMIUM_MODULE)).default:null;
 const browser=await chromium.launch(process.env.CHROMIUM_EXECUTABLE?{executablePath:process.env.CHROMIUM_EXECUTABLE,headless:true,args:['--no-sandbox']}:alt?{executablePath:await alt.executablePath(),args:alt.args,headless:true}:{headless:true});
 const context=await browser.newContext();const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const base=process.env.TEST_BASE_URL||'http://127.0.0.1:8001';
 await page.goto(base);
 await page.locator('#username').fill('teacher');await page.locator('#password').fill(process.env.TEST_ADMIN_PASSWORD);
 await page.locator('#login button[type=submit]').click();await page.getByText('选文章，不用手动录入',{exact:true}).waitFor();await page.getByText('已有教学文章 / 补充录入',{exact:true}).click();await page.getByText('＋ 自定义文章 / 编辑当前文章',{exact:true}).click();
 await page.locator('#title').fill('雨夜的灯');await page.locator('#content').fill('母亲在灯下等我归来。');await page.locator('#articleForm button[type=submit]').click();
 await page.getByText('手动补充 / 修改知识点',{exact:true}).click();await page.locator('#name').fill('意象与象征');await page.locator('#description').fill('能引用细节说明意象的情感含义。');await page.locator('#pointForm button[type=submit]').click();await page.getByText('知识点已保存。',{exact:true}).waitFor();
 await page.locator('[data-tab=questions]').click();await page.locator('#questionForm').waitFor();
 for(const level of ['基础','巩固','拓展']){
  await page.locator('[name=level]').selectOption(level);await page.locator('#material').fill('夜色里，门前那盏灯一直亮着。');await page.locator('#prompt').fill(level+'：分析灯的象征意义。');await page.locator('#reference').fill('灯象征家庭的温暖和母亲的守候。');await page.locator('#rubric').fill('依据五分，分析五分。');await page.locator('#questionForm button[type=submit]').click();await page.getByText(level+'：分析灯的象征意义。',{exact:true}).waitFor();
 }
 await page.locator('details.exercise summary').first().click();await page.locator('[data-edit-question]').first().click();await page.locator('#prompt').fill('基础：引用细节分析灯的象征意义。');await page.locator('#questionForm button[type=submit]').click();await page.getByText('基础：引用细节分析灯的象征意义。',{exact:true}).waitFor();
 await page.locator('[data-tab=assignments]').click();await page.locator('#student').fill('测试学生');await page.locator('#assignmentForm button[type=submit]').click();await page.getByText('任务已生成，复制右侧专属链接发送给该学生。',{exact:true}).waitFor();
 const taskUrl=await page.locator('input[readonly]').first().inputValue();
 const studentContext=await browser.newContext();const student=await studentContext.newPage();student.on('pageerror',e=>errors.push(e.message));await student.goto(taskUrl);
 assert.equal(await student.getByText('灯象征家庭的温暖和母亲的守候。',{exact:true}).count(),0);
 await student.locator('#answer').fill('灯说明家人在等我。');await student.locator('#answerForm button[type=submit]').click();await student.getByText('已提交，等待教师复核。',{exact:true}).waitFor();
 await page.locator('[data-tab=reviews]').click();await page.locator('[name^=score-]').fill('6');await page.locator('[name^=issue-]').fill('文本依据不足');await page.locator('[name^=feedback-]').fill('请引用“一直亮着”，说明守候的含义。');await page.locator('[id^=review-] button[type=submit]').click();await page.getByText('复核已保存，学生可在原任务链接中查看。',{exact:true}).waitFor();
 await page.locator('details.exercise summary').first().click();await page.locator('[id^=follow-]').locator('select').selectOption({index:0});await page.locator('[id^=follow-] button[type=submit]').click();await page.getByText('巩固任务已关联，学生可在原任务页查看新任务。',{exact:true}).waitFor();
 await student.locator('#refresh').click();await student.getByText('教师已复核 · 6/10 分',{exact:true}).waitFor();await student.getByRole('link',{name:'开始巩固训练 1 →'}).click();await student.locator('#answer').fill('“一直亮着”的灯寄托家庭的守候。');await student.locator('#answerForm button[type=submit]').click();await student.getByText('已提交，等待教师复核。',{exact:true}).waitFor();
 await page.reload();await page.locator('[data-tab=reviews]').click();await page.locator('[id^=review-]').nth(1).waitFor({state:'attached'});assert.equal(await page.locator('[id^=review-]').count(),2);
 await page.setViewportSize({width:390,height:844});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
 await page.screenshot({path:'/tmp/zhiyu-teacher-mobile.png',fullPage:true});assert.deepEqual(errors,[]);
 console.log('PASS: teacher login, article/point persistence, three levels, question editing, independent student submission, review, linked reinforcement, reload, mobile layout, no JS errors.');await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
