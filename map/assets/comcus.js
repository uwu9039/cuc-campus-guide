$(function () {
	$(".search-submit").click(function (event) {
		$(this).removeAttr("name");
		event.preventDefault();
		var val = $.trim($(".search-title").val());
		
			$(".wp-search").find("form").submit();
		
		return false;
	});

//$(".wp-search form").attr("method","get")

	var endate2 = ['Jan', 'Feb', 'Mar', 'Apr ', 'May', 'Jun', 'Jul', 'Aug', 'Sept', 'Oct', 'Nov', 'Dec']
	$(".news_meta .news_month").each(function () {
		$(this).text(endate2[parseInt($(this).text()) - 1])
	})
	var monthArr = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十", "十一", "十二"]
	$(".news_months").each(function () {
		var num = parseInt($(this).text())
		$(this).text(monthArr[num - 1] + "月")
	})
      $(".nav .wp-menu .menu-item").each(function () {
           if($(this).children().length==1){
                  $(this).addClass("no-sub")
            }
	})
var newHref = "/_s5/_t724/xxgk/list.psp#ky-main2";
$("li.sub-item.i2-2 a.sub-link").attr("href", newHref);


var newHref2 = "/_s5/_t724/xxgk/list.psp#ky-main4";
$("li.sub-item.i2-5 a.sub-link").attr("href", newHref2);
     $("html").css("scroll-padding-top",document.querySelector(".headfix").offsetHeight)
  
});
fontSize();
$(window).resize(function () {
	fontSize();
});

function fontSize() {
	var size;
	var winW = window.innerWidth;

	if (winW <= 4500 && winW > 1920) {
		size = Math.round(winW / 19.2);
	} else if (winW <= 1920 && winW > 1720) {
		size = 100;
	} else if (winW <= 1720 && winW > 999) {
		size = Math.round(winW / 17.2);
	} else if (winW <= 999) {
		size = 65;
	}

	$('html').css({
		'font-size': size + 'px'
	})
  $(".foot-bottom .top").on("click", function () {		//滚动速度
       $("body,html").stop().animate({ scrollTop: 0 }, 600);
  
    });
   
}






