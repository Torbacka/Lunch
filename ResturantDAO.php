<?php
require_once "configuration.php"; 

class ResturantDAO{
	var $place_id_samtrafiken;
	var $max_walking_distance;

	function ResturantDAO() {
		$this->place_id_samtrafiken = "ChIJVVVV6WCdX0YRC0rrPp8ib6Q";
		$this->max_walking_distance = 850;
	}
	function getPlaceId($id){
	    if(!($mysqli = mysqli_connect(DB_HOST,DB_USER,DB_PASSWORD, DB_NAME))){
	        echo "Det här gick ju inte så bra!";
	    }
	    if($stmt = $mysqli->prepare("SELECT place_id FROM restaurant_info WHERE id = ?")){
	        $stmt->bind_param("d", $id);
	        $stmt->execute();
	        $stmt->bind_result($place_id);
	        $stmt->fetch();
	        $stmt->close();
	    }
	    $mysqli->close();
	    return $place_id;
	}


	function getNumberOfResturants(){
	    $numberOfRows = 0;
	    if(!($mysqli = mysqli_connect(DB_HOST,DB_USER,DB_PASSWORD, DB_NAME))){
	        echo "Det här gick ju inte så bra!";
	    }
	    if($result = $mysqli->query("SELECT COUNT(*) FROM restaurant_info")){
	            $row = $result->fetch_assoc();
	            foreach($row as $cname => $cvalue){
	                $numberOfRows = $cvalue;
	            }

	        $result->close();
	    }else{
	        echo "Gick inte så bra att göra SELECT COUNT(*)";
	    }
	    $mysqli->close();
	    return $numberOfRows;
	}


	function load_resturants(){

		$placeSearchURL = "https://maps.googleapis.com/maps/api/place/radarsearch/json?location=59.3298875,18.0571345&radius=500&type=restaurant&key=".MAP_KEY;
		$data = file_get_contents($placeSearchURL);
		$placesArray = json_decode($data);

		$mysqli = mysqli_connect(DB_HOST,DB_USER,DB_PASSWORD, DB_NAME);
		if (!$mysqli){
				echo "Det här gick ju inte så bra!";
		}
		$mysqli->query("TRUNCATE restaurant_info;");

		$stmt = $mysqli->prepare("INSERT INTO restaurant_info (place_id, latitud, longitud,distance) VALUES (?,?,?,?)");
		if (!$stmt){
				echo "Det gick inte så bra att göra prepare";
		}
		$stmt->bind_param("sssd", $place_id, $latitud,$longitud,$distance); 
		foreach ($placesArray->results as $value) {

			$place_id = $value->place_id;
			$distance = $this->findDistance($place_id);

			$latitud = $value->geometry->location->lat;
			$longitud = $value->geometry->location->lng;
			$this->addImageForRestaurant($place_id, $latitud,$longitud);
			$stmt->execute();

		}
		$mysqli->close();
	}

	function getDistance($place_id){
		 if(!($mysqli = mysqli_connect(DB_HOST,DB_USER,DB_PASSWORD, DB_NAME))){
	        echo "Det här gick ju inte så bra!";
	    }
	    if($stmt = $mysqli->prepare("SELECT distance FROM restaurant_info WHERE id = ?")){
	        $stmt->bind_param("d", $place_id);
	        $stmt->execute();
	        $stmt->bind_result($distance);
	        $stmt->fetch();
	        $stmt->close();
	    }
	    $mysqli->close();
	    return $distance;
	}
	function addImageForRestaurant($place_id,$latidud, $longitud){
		$imageSearchURL =  "https://maps.googleapis.com/maps/api/staticmap?center=".$latidud.",".$longitud."&zoom=15&size=800x400&markers=color:blue%7Clabel:M|".$latidud.",".$longitud."|&key=AIzaSyBSwIaJb7LBn2btW1mcr1fJ-wi-6KZS00M";
        $path ='images/'.$place_id. ".jpg";
        $data = file_get_contents($imageSearchURL);
        $file = fopen($path, 'w');
        fwrite($file, $data);
        fclose($file);
		//Save the data to image folder


	}
	function findDistance($place_id){
		$placeSearchURL = "https://maps.googleapis.com/maps/api/directions/json?origin=place_id:".
							$this->place_id_samtrafiken."&destination=place_id:".$place_id."&mode=walking&key=".MAP_KEY;

		$data = file_get_contents($placeSearchURL);
		$directionsArray = json_decode($data);
		$distance = $directionsArray->routes[0]->legs[0]->distance->value;
		return $distance;
	}
}


?>
