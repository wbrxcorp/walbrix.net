angular.module("WalbrixNet", ["ui.bootstrap","ngResource"])
.controller("DownloadController", ["$scope", "$resource", "$modal", function($scope, $resource, $modal) {
    $scope.send_fast_download_link = function() {
        $scope.progress_message = "送信中...";
        var modalInstance = $modal.open({templateUrl:"progress.html", scope: $scope, backdrop:"static",keyboard:false});
        $resource("./api/send_download_link").save({}, {email:$scope.email}, function(data) {
            modalInstance.close();
            if (data.success) {
                $scope.message = "メールが " + data.info + " に送信されました。";
                $scope.email = null;
            } else {
                if (data.info == "ALREADYSENT") {
                    $scope.message = "メールは既に送信されています。再度送信するには1分間ほど時間をあけてください。";
                } else {
                    $scope.message = "メールの送信に失敗しました。" + data.info;
                }
            }
        }, function() {
            modalInstance.close();
            $scope.message = "通信エラーが発生しました。"
        });
    }
}])
